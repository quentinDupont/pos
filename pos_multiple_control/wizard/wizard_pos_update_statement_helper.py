# Copyright 2020 ForgeFlow, S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class WizardPOSBankStatementUpdateBalanceHelper(models.TransientModel):
    _name = "wizard.pos.update.bank.statement.helper"
    _description = 'POS Update Bank Statement Helper'

    def _default_session_id(self):
        return self.env.context.get('active_pos_id', False)

    item_ids = fields.One2many(
        comodel_name="wizard.pos.update.bank.statement.helper.line",
        inverse_name="wiz_id",
        string="Items",
    )

    wiz_balance_id = fields.One2many(
        comodel_name='wizard.pos.update.bank.statement.balance', string="Wizard Update",
        inverse_name="helper_id",
        required=True)

    total = fields.Float(
        string="Total",
        compute="_compute_helper_total",
    )

    @api.model
    def _prepare_item(self, statement):
        return {
            "statement_id": statement.id,
            "name": statement.name,
            "journal_id": statement.journal_id.id,
            "balance_start": statement.balance_start,
            "balance_end": statement.balance_end,
            "total_entry_encoding": statement.total_entry_encoding,
            "currency_id": statement.currency_id.id,
        }

    @api.model
    def default_get(self, flds):
        res = super().default_get(flds)
        # Load objects
        # session_obj = self.env["pos.session"]
        # bank_statement_obj = self.env["account.bank.statement"]
        # Load context
        active_ids = self.env.context["active_id"] or []
        # active_pos_id = self.env.context["active_pos_id"] or []
        active_model = self.env.context["active_model"] or []
        # balance_moment = self.env.context["balance_moment"] or []
        # Check propagation
        # if not active_pos_id:
        #     return res
        # assert active_model == "pos.session", \
        #     "Bad context propagation"
        # if len(active_pos_id) > 1:
        #     raise UserError(_('You cannot start the closing '
        #                       'balance for multiple POS sessions'))
        # Add bank statement lines
        # session = session_obj.browse(active_pos_id[0])
        # bank_statement = bank_statement_obj.browse(active_ids[0])
        items = []
        # items.append([0, 0, self._prepare_item(bank_statement)])
        # Give values for wizard
        # res["session_id"] = session.id
        res["item_ids"] = items
        # res["balance_moment"] = balance_moment
        # res["journal_id"] = bank_statement.journal_id.id
        return res

    # @api.model
    # def _prepare_cash_box_journal(self, item):
    #     return {
    #         'amount': abs(item.difference),
    #         'name': _('Out'),
    #         "journal_id": item.journal_id.id,
    #     }


    @api.multi
    @api.depends("item_ids.subtotal")
    def _compute_helper_total(self):
        for line in self.item_ids:
            self.total += line.subtotal


    @api.multi
    def action_confirm_helper(self):
        # REUSSIR À CHOPPER LE CONTEXT, LE BON wizard.pos.update.bank.statement.balance.line
        # PEUT ETRE LE PASSER DANS LE DEFAULT GET J'IMAGINE
        
        import pdb; pdb.set_trace()
        self.wiz_balance_id.item_ids.balance_end_real = self.total
        self.ensure_one()
        # record new values from wizard
        # for item in self.item_ids:
        #     if item.balance_moment == 'starting':
        #         item.statement_id.balance_start = item.balance_start_real
        #     elif item.balance_moment == 'ending':
        #         item.statement_id.balance_end_real = item.balance_end_real
        #         # item.statement_id.balance_end = item.balance_end_real
        return True


class WizardPOSBankStatementUpdateBalanceHelperLine(models.TransientModel):
    _name = "wizard.pos.update.bank.statement.helper.line"
    _description = 'POS Update Bank Statement Helper Line'

    wiz_id = fields.Many2one(
        comodel_name='wizard.pos.update.bank.statement.helper',
        required=True,
    )
    # Columns Section
    coin_value = fields.Float(
        string="Coin Value",
    )

    number = fields.Float(
        string="Number",
    )

    subtotal = fields.Float(
        string="Subtotal",
        compute="_compute_helper_subtotal",
    )

    # statement_id = fields.Many2one(
    #     comodel_name='account.bank.statement',
    # )
    # name = fields.Char(
    #     related='statement_id.name'
    # )
    # journal_id = fields.Many2one(
    #     comodel_name='account.journal',
    #     related='statement_id.journal_id',
    # )
    # balance_start = fields.Monetary(
    #     string="Starting Balance",
    #     default=0.0,
    #     compute='_compute_balance_start'
    # )
    # balance_start_real = fields.Monetary(
    #     default=0.0
    # )
    # total_entry_encoding = fields.Monetary(
    #     related='statement_id.total_entry_encoding',
    # )
    # balance_end = fields.Monetary(
    #     string="Computed Balance",
    #     default=0.0,
    #     compute='_compute_balance_end'
    # )
    # balance_end_real = fields.Monetary(
    #     default=0.0
    # )
    # currency_id = fields.Many2one(
    #     comodel_name='res.currency',
    #     related='statement_id.currency_id'
    # )
    # balance_moment = fields.Selection(
    #     related='wiz_id.balance_moment',
    #     default='bydefault')

    @api.multi
    @api.depends("coin_value","number")
    def _compute_helper_subtotal(self):
        for rec in self:
            rec.subtotal = rec.coin_value * rec.number

    # def _compute_balance_end(self):
    #     for rec in self:
    #         rec.balance_end = rec.statement_id.balance_end
