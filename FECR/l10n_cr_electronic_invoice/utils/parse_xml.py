import base64
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from lxml import etree, objectify
from email.message import EmailMessage

_logger = logging.getLogger(__name__)

def parseXml(self,values,attachments,invoice_import_ids):
    vals = {}
    for att in attachments:
        if att and att.fname[-3:] == "xml":
            rs = data_xml(self,att,invoice_import_ids)
            vals.update(rs)
    return vals

def data_xml(self,att,invoice_import_ids):
    #xml_string = re.sub(' xmlns="[^"]+"',"",att.content,count=1,).encode("utf-8")
    #root = ET.fromstring(xml_string)

    #xml_decoded = base64.b64decode(xml_string)
    #xml_decoded = att.content

    #xml_string_encode = re.sub(' xmlns="[^"]+"', "", att.content).encode("utf-8")

    #at = base64.encodebytes(xml_string_encode)

    content= att.content
    if isinstance(content, str):
        content = content.encode('utf-8')
    elif isinstance(content, EmailMessage):
        content = content.as_bytes()

    xml_code = base64.b64encode(content)
    xml_string = re.sub(
        ' xmlns="[^"]+"',
        "",
        base64.b64decode(xml_code).decode("utf-8"),
        count=1,
    ).encode("utf-8")
    root = ET.fromstring(xml_string)

    xml_decoded = base64.b64decode(xml_code)

    try:
        factura = etree.fromstring(xml_decoded)

    except Exception as e:
        _logger.error("MAB - This XML file is not XML-compliant. Exception {}".format(e))
        return {"status": 400, "text": "Excepción de conversión de XML"}

    #pretty_xml_string = etree.tostring(factura, pretty_print=True, encoding="UTF-8", xml_declaration=True)
    #_logger.info("Send_file XML: {}".format(pretty_xml_string))


    if root.tag == 'FacturaElectronica':
        r=1
        namespaces = factura.nsmap
        inv_xmlns = namespaces.pop(None)
        namespaces["inv"] = inv_xmlns

        consecutive_number_receiver = factura.xpath("inv:NumeroConsecutivo", namespaces=namespaces)[0].text
        payment_reference = consecutive_number_receiver
        number_electronic = factura.xpath("inv:Clave", namespaces=namespaces)[0].text
        date_issuance = factura.xpath("inv:FechaEmision", namespaces=namespaces)[0].text
        if "." in date_issuance:  # Time with milliseconds
            date_issuance = date_issuance[: date_issuance.find(".") + 7]  # Truncate first 6 digits of seconds
        date_formats = [
            "%Y-%m-%dT%H:%M:%S-06:00",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
        ]
        for date_format in date_formats:
            try:
                date_time_obj = datetime.strptime(date_issuance, date_format)
                break
            except ValueError:
                continue
        else:
            _logger.error("No valid date format for {}").format(date_issuance)
            r = 0
        invoice_date = date_time_obj.date()

        try:
            emisor = factura.xpath("inv:Emisor/inv:Identificacion/inv:Numero", namespaces=namespaces)[0].text
        except IndexError:
            _logger.error("The issuer has no identification number, the xml received is invalid")
            r = 0

        try:
            receptor = factura.xpath("inv:Receptor/inv:Identificacion/inv:Numero", namespaces=namespaces)[0].text
        except IndexError:
            _logger.error("The receiver has no identification number, the xml received is invalid")
            r = 0

        currency_node = factura.xpath("inv:ResumenFactura/inv:CodigoTipoMoneda/inv:CodigoMoneda",namespaces=namespaces)

        tipo_cambio = factura.xpath("inv:ResumenFactura/inv:CodigoTipoMoneda/inv:TipoCambio",namespaces=namespaces,)
        if currency_node:
            currency_id = self.env["res.currency"].search([("name", "=", currency_node[0].text)], limit=1).id
            rate_currency = self.env['res.currency.rate'].sudo().search([('name', '=', str(date_issuance))])
            if not rate_currency and tipo_cambio:
                rate_currency = self.env['res.currency.rate'].sudo().create({'name': invoice_date,
                                                                      'rate': round((1 / float(tipo_cambio[0].text)), 12),
                                                                      'currency_id': currency_id,
                                                                      'company_id': self.env.company.id,
                                                                      })

        else:
            currency_id = self.env["res.currency"].sudo().search([("name", "=", "CRC")], limit=1).id

        if receptor != self.env.company.vat:
            _logger.error("The receiver does not correspond to the current company with identification {}. Please activate the correct company.").format(receptor)
            r = 0

        partner = self.env["res.partner"].sudo().search([("vat", "=", emisor),
                                                  ("supplier_rank", ">", 0),
                                                  "|",
                                                  ("company_id", "=", self.env.company.id),
                                                  ("company_id", "=", False),
                                                  ],limit=1,)

        if partner:
            partner_id = partner.id
        else:
            partner_id = create_partner(self, factura, namespaces)
            #_logger.error("The provider with id {} does not exist. Please create it in the system first.").format(emisor)
            #r = 0

        #EXTRAS:
        condicion_venta_code = factura.xpath("inv:CondicionVenta", namespaces=namespaces)[0].text
        sale_condition = self.env['sale.conditions'].sudo().search([('sequence','=',condicion_venta_code)],limit=1)
        termino_pago = self.env['account.payment.term'].sudo().search([('sale_conditions_id','=',sale_condition.id)],limit=1)

        medio_pago_code = factura.xpath("inv:MedioPago", namespaces=namespaces)[0].text
        medio_pago = self.env['payment.methods'].sudo().search([('sequence','=',medio_pago_code)],limit=1)

        tax_node = factura.xpath("inv:ResumenFactura/inv:TotalImpuesto", namespaces=namespaces)
        if tax_node:
            amount_tax_electronic_invoice = tax_node[0].text

        amount_total_electronic_invoice = factura.xpath("inv:ResumenFactura/inv:TotalComprobante", namespaces=namespaces)[0].text

        lines = root.find("DetalleServicio").findall("LineaDetalle")

        account = invoice_import_ids.account_id
        tax_ids = invoice_import_ids.tax_ids
        journal_id = invoice_import_ids.journal_id.id

        if r:
            values = {
                'name': '/',
                'tipo_documento': 'FEC',
                'move_type': 'in_invoice',
                'ref': consecutive_number_receiver or False,
                'journal_id': journal_id,
                'consecutive_number_receiver': consecutive_number_receiver,
                #'payment_reference': payment_reference,
                'number_electronic': number_electronic,
                'date_issuance': date_issuance,
                'invoice_date': date_issuance,
                'date': date_issuance,
                'invoice_date': invoice_date,
                'currency_id': currency_id,
                'partner_id': partner_id,
                'invoice_payment_term_id': termino_pago.id or False,
                'payment_method_id': medio_pago.id or False,
                'amount_tax_electronic_invoice': amount_tax_electronic_invoice,
                'amount_total_electronic_invoice': amount_total_electronic_invoice,
                'invoice_line_ids': data_line(self, att, lines, account, tax_ids)
            }

        else:
            values = {}

        return values
    else:
        return {}



def data_line(self, att, lines, account, tax_ids):
    """Preparando lineas de factura"""

    array_lines = []
    for line in lines:
        product_uom = self.env["uom.uom"].sudo().search([("code", "=", line.find("UnidadMedida").text)], limit=1).id
        total_amount = float(line.find("MontoTotal").text)
        discount_percentage = 0.0
        discount_note = None
        discount_node = line.find("Descuento")
        if discount_node:
            discount_amount_node = discount_node.find("MontoDescuento")
            discount_amount = float(discount_amount_node.text or "0.0")
            discount_percentage = discount_amount / total_amount * 100
            discount_note = discount_node.find("NaturalezaDescuento").text
        else:
            discount_amount_node = line.find("MontoDescuento")
            if discount_amount_node:
                discount_amount = float(discount_amount_node.text or "0.0")
                discount_percentage = discount_amount / total_amount * 100
                discount_note = line.find("NaturalezaDescuento").text

        taxes = self.env["account.tax"]
        tax_nodes = line.findall("Impuesto")
        total_tax = 0.0

        if tax_nodes:
            for tax_node in tax_nodes:
                if tax_node:
                    tax_amount = float(tax_node.find("Monto").text)
                    if tax_amount > 0:
                        tax_code = re.sub(r"[^0-9]+", "", tax_node.find("Codigo").text)
                        tax = self.env["account.tax"].sudo().search([("tax_code", "=", tax_code),
                                                                    ("amount", "=", tax_node.find("Tarifa").text),
                                                                    ("type_tax_use", "=", "purchase")],limit=1,)
                        if tax:
                            taxes += tax
                            total_tax += tax_amount
                        else:
                            _logger.error("A tax type in the XML does not exist in the configuration: {}").format(tax_node.find("Codigo").text)

        account_id = account.id

        data = {
            #'sequence': line.find("NumeroLinea").text,
            'name': line.find("Detalle").text,
            'price_unit': line.find("PrecioUnitario").text,
            'quantity': line.find("Cantidad").text,
            'product_uom_id': product_uom,
            'discount': discount_percentage,
            'discount_note': discount_note,
            'tax_ids': taxes,
            'total_tax': total_tax,
            'account_id': account_id,
        }
        array_lines.append((0,0,data))

    return array_lines


def create_partner(self,factura, namespaces):

    name = factura.xpath("inv:Emisor/inv:Nombre", namespaces=namespaces)[0].text
    type_code = factura.xpath("inv:Emisor/inv:Identificacion/inv:Tipo", namespaces=namespaces)[0].text
    vat = factura.xpath("inv:Emisor/inv:Identificacion/inv:Numero", namespaces=namespaces)[0].text
    provincia_code = factura.xpath("inv:Emisor/inv:Ubicacion/inv:Provincia", namespaces=namespaces)[0].text
    canton_code = factura.xpath("inv:Emisor/inv:Ubicacion/inv:Canton", namespaces=namespaces)[0].text
    distrito_code = factura.xpath("inv:Emisor/inv:Ubicacion/inv:Distrito", namespaces=namespaces)[0].text
    barrio_code = factura.xpath("inv:Emisor/inv:Ubicacion/inv:Barrio", namespaces=namespaces)[0].text
    telefono_code = factura.xpath("inv:Emisor/inv:Telefono/inv:NumTelefono", namespaces=namespaces)[0].text
    pais_id = self.env.company.country_id.id
    if type_code:
        type_id = self.env['identification.type'].sudo().search([('code','=', type_code)],limit=1)
    if provincia_code:
        provincia = self.env['res.country.state'].sudo().search([('code','=',provincia_code),('country_id','=',pais_id)])
    if canton_code:
        canton = self.env['res.country.county'].sudo().search([('code','=',canton_code),('state_id','=',provincia.id)])
    if distrito_code:
        distrito = self.env['res.country.district'].sudo().search([('code','=',distrito_code),('county_id','=',canton.id)])
    if barrio_code:
        barrio = self.env['res.country.neighborhood'].sudo().search([('code','=',barrio_code),('district_id','=',distrito.id)])

    partner_vals = {
        'name': name,
        'identification_id': type_id.id,
        'vat': vat,
        'country_id': pais_id,
        'state_id': provincia.id or False,
        'county_id': canton.id or False,
        'district_id': distrito.id or False,
        'neighborhood_id': barrio.id or False,
        'phone': telefono_code,
        'supplier_rank': 99
    }

    partner = self.env['res.partner'].sudo().create(partner_vals)
    return partner.id
