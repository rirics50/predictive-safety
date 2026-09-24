from odoo import http
from odoo.http import request
import json

class PredictiveSafetyController(http.Controller):

    @http.route('/api/equipment/<string:equipment_name>', type='http', auth='public', methods=['GET'], csrf=False)
    def get_equipment_spec(self, equipment_name, **kwargs):
        equipment = request.env['predictive.safety.pipeline'].sudo().search(
            [('name', '=', equipment_name)], limit=1
        )
        if not equipment:
            body = json.dumps({'error': f'No equipment found with name "{equipment_name}"'})
            return request.make_response(body, headers=[('Content-Type', 'application/json')], status=404)

        data = {
            'name': equipment.name,
            'material': equipment.material,
            'grade': equipment.grade,
            'diameter': equipment.diameter,
            'thickness': equipment.thickness,
            'corrosion_allowance': equipment.corrosion_allowance,
            'design_temperature': equipment.design_temperature,
            'design_pressure': equipment.design_pressure,
        }
        return request.make_response(json.dumps(data), headers=[('Content-Type', 'application/json')])
