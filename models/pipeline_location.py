from odoo import models, fields


class PipelineLocation(models.Model):
    """One monitored location on a piece of equipment. The location strings
    are fixed (they match the CoppeliaSim signal names), and the equipment's
    design_pressure/design_temperature are the shared safety limits for all
    of its locations - only flow and pipe length vary per location."""
    _name = 'predictive.safety.location'
    _description = 'Monitored Location'
    _order = 'equipment_id, id'

    equipment_id = fields.Many2one('predictive.safety.pipeline', string='Equipment', required=True, ondelete='cascade')
    location = fields.Selection([
        ('feed_pipeline', 'Feed Pipeline'),
        ('distillate_output', 'Distillate Output'),
        ('bottoms_output', 'Bottoms Output'),
        ('column_bottom', 'Column Bottom'),
        ('column_top', 'Column Top'),
    ], string='Location', required=True)
    flow_limit = fields.Float(string='Flow Limit (kg/s)')
    pipe_length = fields.Float(string='Pipe Length (m)')

    _equipment_location_unique = models.Constraint(
        'unique(equipment_id, location)',
        'Each location can only appear once per piece of equipment.',
    )
