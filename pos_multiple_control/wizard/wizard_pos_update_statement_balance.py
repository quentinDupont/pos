# Copyright 2020 ForgeFlow, S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class WizardUpdateBankStatement(models.TransientModel):
    _name = "wizard.update.bank.statement"
    _description = 'POS Update Bank Statement Balance'

    def _default_session_id(self):
        return self.env.context.get('active_pos_id', False)

# NOUVEAU
# FIN NOUVEAU
    _BALANCE_MOMENT_SELECTION = [
        ('bydefault', 'Default'),
        ('starting', 'Starting balance'),
        ('ending', 'Ending balance'),
    ]

    item_ids = fields.One2many(
        comodel_name="wizard.update.bank.statement.line",
        inverse_name="wiz_id",
        string="Items",
    )

    balance_moment = fields.Selection(
        selection=_BALANCE_MOMENT_SELECTION, string='Balance moment',
        default='bydefault')

    journal_id = fields.Many2one(
        comodel_name='account.journal', string="Journal",
        domain="[('id', 'in', journal_ids)]", required=True)

    session_id = fields.Many2one(
        comodel_name='pos.session', string="Current Session",
        default=_default_session_id, required=True, readonly=True)

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='journal_id.currency_id'
    )

    @api.multi
    @api.depends('cashbox_lines.subtotal')
    def _compute_balance_end_real_up(self):
        print("========= _compute_balance_end_real_up")
        balance_end_real_up = 0.0
        for cashbox_lines in self.cashbox_lines:
            balance_end_real_up += cashbox_lines.subtotal
        print("========= _compute_balance_end_real_up ; return : " + str(balance_end_real_up))
        self.balance_end_real_up = balance_end_real_up
        # Write in context for xml readonly field
        context = self.env.context.copy()
        context.update({'balance_end_real_up': balance_end_real_up})
        self.env.context = context
        # import pdb; pdb.set_trace()
        # self.env.context.update({'balance_end_real_up': balance_end_real_up})
        # return balance_end_real_up
        return balance_end_real_up


    balance_end_real_up = fields.Monetary(
        compute='_compute_balance_end_real_up',
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
        session_obj = self.env["pos.session"]
        bank_statement_obj = self.env["account.bank.statement"]
        cashbox_lines_obj = self.env["account.cashbox.line"]
        # Load context
        active_ids = self.env.context["active_id"] or []
        active_pos_id = self.env.context["active_pos_id"] or []
        active_model = self.env.context["active_model"] or []
        balance_moment = self.env.context["balance_moment"] or []
        # Check propagation
        if not active_pos_id:
            return res
        assert active_model == "pos.session", \
            "Bad context propagation"
        if len(active_pos_id) > 1:
            raise UserError(_('You cannot start the closing '
                              'balance for multiple POS sessions'))
        # Add bank statement lines
        session = session_obj.browse(active_pos_id[0])
        bank_statement = bank_statement_obj.browse(active_ids[0])
        items = []
        items.append([0, 0, self._prepare_item(bank_statement)])
        # cashbox_lines = cashbox_lines_obj.search(['accountbs_id', '=', active_ids[0]])
        # Give values for wizard
        res["session_id"] = session.id
        res["item_ids"] = items
        res["balance_moment"] = balance_moment
        res["journal_id"] = bank_statement.journal_id.id
        res["cashbox_lines"] = self._default_cashbox_lines()
        return res


    @api.model
    def _prepare_cashbox_lines(self, line):
        return {
            "coin_value": line.coin_value,
            "number": line.number,
            "subtotal": line.subtotal,
        }

    @api.model
    def _default_cashbox_lines(self):
        # import pdb; pdb.set_trace()
        # Load objects
        # session_obj = self.env["pos.session"]
        bank_statement_obj = self.env["account.bank.statement"]
        # Load context
        active_ids = self.env.context["active_id"] or []
        # active_pos_id = self.env.context["active_pos_id"] or []
        # active_model = self.env.context["active_model"] or []
        # balance_moment = self.env.context["balance_moment"] or []
        # Add bank statement lines
        # session = session_obj.browse(active_pos_id[0])
        bank_statement = bank_statement_obj.browse(active_ids[0])
        items = []
        for line in bank_statement.cashbox.cashbox_lines_ids:
            items.append([0, 0, self._prepare_cashbox_lines(line)])
        return items

    # cashbox_lines = fields.One2many(
    #     comodel_name='wizard.update.cashbox.line',
    #     default=_default_cashbox_lines,)

    cashbox_lines = fields.One2many(
        comodel_name='wizard.update.cashbox.line',
        default=_default_cashbox_lines,
        inverse_name='wiz_id')

    @api.model
    def _prepare_cash_box_journal(self, item):
        return {
            'amount': abs(item.difference),
            'name': _('Out'),
            "journal_id": item.journal_id.id,
        }

    @api.multi
    def action_confirm(self):
        self.ensure_one()
        # record new values from wizard
        for item in self.item_ids:
            if item.balance_moment == 'starting':
                item.statement_id.balance_start = item.balance_start_real
            elif item.balance_moment == 'ending':
                if self.balance_end_real_up !=0:
                    print("==== BALANCE END nouveau")
                    item.statement_id.balance_end_real = self.balance_end_real_up
                    # Load object
                    cashbox_obj = self.env["account.bank.statement.cashbox"]
                    cashbox_line_obj = self.env["account.cashbox.line"]
                    bank_statement_obj = self.env["account.bank.statement"]
                    # Load context
                    active_ids = self.env.context["active_id"] or []
                    bank_statement = bank_statement_obj.browse(active_ids[0])

                    # Create the WizardUpdateCashboxLine
                    _cashbox = cashbox_obj.create({})
                    for line in self.cashbox_lines:
                        cashbox_line_obj.create({
                            'coin_value': line.coin_value,
                            'number': line.number,
                            'subtotal': line.subtotal,
                            'cashbox_id': _cashbox.id,})
                    # Save the WizardUpdateCashboxLine in bank_statement
                    bank_statement.write({'cashbox' : _cashbox.id,})
                    # item.cashbox = _cashbox
                    # import pdb; pdb.set_trace()
                    print("==== BALANCE END nouveau - On crée le cashbox qui sera saved, id")
                    print("==== Cashbox, id : " + str(_cashbox.id))
                    print("==== bank_statement, id : " + str(bank_statement.id))

                else:
                    print("==== BALANCE END ancien")
                    item.statement_id.balance_end_real = item.balance_end_real
                    item.statement_id.balance_end = item.balance_end_real
        return True


class WizardUpdateBankStatementLine(models.TransientModel):
    _name = "wizard.update.bank.statement.line"
    _description = 'POS Update Bank Statement Balance Line'

    wiz_id = fields.Many2one(
        comodel_name='wizard.update.bank.statement',
        required=True,
    )

    statement_id = fields.Many2one(
        comodel_name='account.bank.statement',
    )
    name = fields.Char(
        related='statement_id.name'
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        related='statement_id.journal_id',
    )
    balance_start = fields.Monetary(
        string="Starting Balance",
        default=0.0,
        compute='_compute_balance_start'
    )
    balance_start_real = fields.Monetary(
        default=0.0
    )
    total_entry_encoding = fields.Monetary(
        related='statement_id.total_entry_encoding',
    )
    balance_end = fields.Monetary(
        string="Computed Balance",
        default=0.0,
        compute='_compute_balance_end'
    )
    balance_end_real = fields.Monetary(
        default=0.0,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='statement_id.currency_id'
    )
    balance_moment = fields.Selection(
        related='wiz_id.balance_moment',
        default='bydefault')

    def _compute_balance_start(self):
        for rec in self:
            rec.balance_start = rec.statement_id.balance_start

    def _compute_balance_end(self):
        for rec in self:
            rec.balance_end = rec.statement_id.balance_end


class WizardUpdateCashboxLine(models.TransientModel):
    _name = 'wizard.update.cashbox.line'

    @api.one
    @api.depends('coin_value', 'number')
    def _sub_total(self):
        """ Calculates Sub total"""
        self.subtotal = self.coin_value * self.number
        # self.wiz_id.balance_end_real_up = self.subtotal // marche pas ça n'enregistre pas
        # import pdb; pdb.set_trace()

    _BALANCE_MOMENT_SELECTION = [
        ('bydefault', 'Default'),
        ('starting', 'Starting balance'),
        ('ending', 'Ending balance'),
    ]

    balance_moment = fields.Selection(
        selection=_BALANCE_MOMENT_SELECTION, string='Balance moment',
        default='bydefault')
    coin_value = fields.Float(string='Coin/Bill Value', required=True, digits=0)
    number = fields.Integer(string='Number of Coins/Bills', help='Opening Unit Numbers')
    subtotal = fields.Float(compute='_sub_total', string='Subtotal', digits=0, readonly=True)
    cashbox_id = fields.Many2one('wizard.update.cashbox', string="Cashbox")
    wiz_id = fields.Many2one('wizard.update.bank.statement', string="Wizard")


class WizardUpdateCashbox(models.TransientModel):
    _name = 'wizard.update.cashbox'

    cashbox_lines_ids = fields.One2many('wizard.update.cashbox.line', 'cashbox_id', string='Cashbox Lines')
    total = fields.Float(compute='_total', string='Total', digits=0, readonly=True)

    @api.multi
    @api.depends('cashbox_lines_ids.subtotal')
    def _total(self):
        print("RECALCULE TOTAL = ")
        _total = 0.0
        for lines in self.cashbox_lines_ids:
            _total += lines.subtotal
        self.total = _total
        print("RECALCULE TOTAL = " + str(_total))
