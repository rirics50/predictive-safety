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

    @http.route('/api/safety_status/<string:equipment_name>', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    def post_safety_status(self, equipment_name, **kwargs):
        equipment = request.env['predictive.safety.pipeline'].sudo().search(
            [('name', '=', equipment_name)], limit=1
        )
        if not equipment:
            return {'error': f'No equipment found with name "{equipment_name}"'}

        status = kwargs.get('status', '').lower()
        reason = kwargs.get('reason')

        if status not in ('safe', 'warning', 'critical'):
            return {'error': f'Invalid status "{status}" - must be safe, warning, or critical'}

        if not equipment.receive_safety_reading(status, pressure=equipment.last_pressure, reason=reason):
            return {
                'error': f'{equipment.name} is latched CRITICAL - Manual Reset in Odoo is required before new statuses apply',
                'status': equipment.current_status,
            }
        return {'ok': True, 'status': status}
