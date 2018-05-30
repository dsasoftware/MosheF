# -*- coding: utf-8 -*-

from openerp import _, api, fields, models
from openerp.exceptions import ValidationError


class IrExports(models.Model):
    _inherit = 'ir.exports'

    name = fields.Char(required=True)
    resource = fields.Char(
        required=False,
        readonly=True,
        help="Model technical name.")
    model_id = fields.Many2one(
        "ir.model",
        "Model",
        store=True,
        domain=[("transient", "=", False)],
        compute="_set_model_id",
        inverse="_set_resource_id",
        help="Database model to export.")
    ir_values_id = fields.Many2one('ir.values', string='More Menu entry', readonly=True,
                                   help='More menu entry.', copy=False)
    ref_ir_value_id = fields.Many2one('ir.values', string='More Menu entry 2', readonly=True,
                                   help='More menu entry.', copy=False)
    ref_ir_act_window_id = fields.Many2one('ir.actions.act_window', string='More Menu entry', readonly=True,
                                   help='More menu entry.', copy=False)
    
    @api.multi
    @api.depends("resource")
    def _set_model_id(self):
        for s in self:
            s.model_id = self._get_model_id(s.resource)

    @api.multi
    @api.onchange("model_id")
    def _set_resource_id(self):
        for s in self:
            s.resource = s.model_id.model    
            
    @api.multi
    @api.onchange("resource")
    def _onchange_resource(self):
        for s in self:
            s.export_fields = False

    @api.model
    def _get_model_id(self, resource):
        return self.env["ir.model"].search([("model", "=", resource)])

    @api.model
    def create(self, vals):
        if not any(f in vals for f in {"model_id", "resource"}):
            raise ValidationError(_("You must supply a model or resource."))
        return super(IrExports, self).create(vals) 
    
    @api.multi
    def create_action1(self):
        """ Create a contextual action for each report. """
        for export in self:
            ir_values = self.env['ir.values'].sudo().create({
                'name': export.name,
                'model': export.resource,
                'res_id': 0,
                'key2': 'client_action_multi',
                'value': "ir.actions.act_window,%s" % export.id,
            })
            export.write({'ir_values_id': ir_values.id})
        return True

    @api.multi
    def unlink_action2(self):
        """ Remove the contextual actions created for the reports. """
        self.check_access_rights('write', raise_exception=True)
        for export in self:
            if export.ir_values_id:
                try:
                    self.ir_values_id.sudo().unlink()
                except Exception:
                    raise UserError(_('Deletion of the action record failed.'))
        return True
    
    @api.multi
    def create_action(self):
        self.ensure_one()
        vals = {}
        action_obj = self.env['ir.actions.act_window']
        src_obj = self.model_id.model
        button_name = _('Export (%s)') % self.name
        vals['ref_ir_act_window_id'] = action_obj.create({
            'name': button_name,
            'type': 'ir.actions.act_window',
            'res_model': 'ir.exports.wizard',
            'src_model': src_obj,
            'view_type': 'form',
            'context': "{'export_editing_object' : %d}" % (self.id),
            'view_mode': 'form, tree',
            'target': 'new',
            'auto_refresh': 1,
        }).id
        vals['ref_ir_value_id'] = self.env['ir.values'].create({
            'name': button_name,
            'model': src_obj,
            'key2': 'client_action_multi',
            'value': "ir.actions.act_window," +
                     str(vals['ref_ir_act_window_id']),
        }).id
        self.write(vals)
        return {'type': 'ir.actions.client','tag': 'reload',}
        #return True

    @api.multi
    def unlink_action(self):
        for export in self:
            try:
                if export.ref_ir_act_window_id:
                    export.ref_ir_act_window_id.unlink()
                if export.ref_ir_value_id:
                    export.ref_ir_value_id.unlink()
            except:
                raise UserError(_("Deletion of the action record failed."))
        return {'type': 'ir.actions.client','tag': 'reload',}
        #return True

    @api.multi
    def unlink(self):
        self.unlink_action()
        return super(IrExports, self).unlink()    