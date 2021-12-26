import uuid

from datetime import date, timedelta
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.translation import gettext as _
from faktura.validators import FileSizeValidator

from .settings import (
    DEFAULT_DUE_DATE,
    DEFAULT_STATUS,
    DEFAULT_TYPE,
    DEFAULT_INCLUDES_VAT,
    DEFAULT_VAT,
    DEFAULT_CURRENCY,
    DEFAULT_DISCOUNT,
    DEFAULT_ITEM_QUANTITY,
    MAX_FILE_SIZE_UPLOAD,
    DEFAULT_ACCOUNT,
)

def get_due_date():
    return date.today() + timedelta(days=DEFAULT_DUE_DATE)


class InvoiceManager(models.Manager):
    """
    Manager at pre-select all related items for each query set.
    """
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related('invoice', 'author').prefetch_related('items')


class Invoice(models.Model):
    DRAFT = "draft"
    FINAL = "final"
    STATUS_CHOICES = ((DRAFT, _("Draft")), (FINAL, _("Final document")))
    INVOICE = "invoice"
    PROFORMA = "proforma invoice"
    CREDIT = "credit note"
    TYPES_CHOICES = (
        (INVOICE, _("Invoice")),
        (PROFORMA, _("Pro forma Invoice")),
        (CREDIT, _("Credit note")),
    )
    objects = InvoiceManager()

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    number = models.CharField(_("Invoice number"), max_length=10, null=True, blank=True)
    date_of_issue = models.DateField(_("Date of issue"), default=date.today)
    due_date = models.DateField(_("Due date"), default=get_due_date)
    seller = models.CharField(_("Issuer"), max_length=1024)
    seller_details = models.TextField(_("Issuer details"))
    buyer = models.CharField(_("Customer"), max_length=1024)
    buyer_details = models.TextField(_("Customer details"))
    status = models.CharField(
        _("Status"), max_length=5, choices=STATUS_CHOICES, default=DEFAULT_STATUS
    )
    type = models.CharField(
        _("Type"), max_length=16, choices=TYPES_CHOICES, default=DEFAULT_TYPE
    )
    includes_vat = models.BooleanField(_("VAT payer"), default=DEFAULT_INCLUDES_VAT)
    vat = models.FloatField(_("VAT"), default=DEFAULT_VAT)
    currency = models.CharField(_("Currency"), default=DEFAULT_CURRENCY, max_length=4)
    discount = models.FloatField(_("Discount"), default=DEFAULT_DISCOUNT)
    note = models.TextField(_("Note"), null=True, blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    invoice = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="proforma",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = (
            ("can_mark_invoice_as_final", 'Can mark invoice as "Final document"'),
        )
        ordering = ["-date_of_issue", "-number"]

    def __str__(self):
        return f"{self.number}: {self.buyer} ({self.date_of_issue})"

    @property
    def items_total(self):
        total = 0

        for item in self.items.all():
            total += item.total_amount

        return total

    @property
    def items_vat(self):
        if not self.includes_vat:
            self.vat = 0

        return self.items_total * self.vat / 100

    @property
    def items_total_with_vat(self):
        return self.items_total + self.items_vat

    @property
    def items_discount(self):
        return self.items_total_with_vat * self.discount / 100

    @property
    def total_amount(self):
        return round(self.items_total_with_vat - self.items_discount, 2)

    def save(self, *args, **kwargs):
        if self.invoice and self.type == Invoice.INVOICE:
            raise ValueError(
                "It is not possible to generate invoice from invoice! Provide pro forma invoice or credit note."
            )

        if self.status == self.FINAL and self.number is None:
            year = self.date_of_issue.year
            this_year_invoices = (
                Invoice.objects.filter(date_of_issue__year=year)
                .filter(type=self.type)
                .filter(status=self.FINAL)
                .order_by("-created_at")
            )
            invoice_number = len(this_year_invoices) + 1

            if self.type == Invoice.PROFORMA:
                self.number = f"P{invoice_number:03}/{year}"
            elif self.type == Invoice.CREDIT:
                self.number = f"C{invoice_number:03}/{year}"
            else:
                self.number = f"{invoice_number:03}/{year}"

        super().save(*args, **kwargs)


class Item(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="items",
        related_query_name="item",
    )
    title = models.TextField(_("Title"))
    price = models.FloatField(_("Unit price"))
    quantity = models.PositiveIntegerField(_("Quantity"), default=DEFAULT_ITEM_QUANTITY)

    def __str__(self):
        return f"{self.invoice}: {self.title}"

    @property
    def total_amount(self):
        return self.price * self.quantity


class Account(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(_("Title"), max_length=255)
    description = models.TextField(_("Description"), null=True, blank=True)
    metadata = models.JSONField(
        verbose_name=_("Metadata"), blank=True, null=True, help_text=_("Metadata about Account.")
    )

    def __str__(self):
        return self.title


def get_default_account():
    return Account.objects.get(title=DEFAULT_ACCOUNT)


class Transaction(models.Model):
    INCOME = 'income'
    EXPENSE = 'expense'
    ASSET = 'asset'
    LIABILITY = 'liability'
    TYPES_CHOICES = (
        (INCOME, _("Income")),
        (EXPENSE, _("Expense")),
        (ASSET, _("Asset")),
        (LIABILITY, _("Liability"))
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField(_("Date"))
    title = models.CharField(_("Title"), max_length=255, null=True, blank=True)
    description = models.TextField(_("Description"), null=True, blank=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, default=get_default_account)
    type = type = models.CharField(_("Type"), max_length=12, choices=TYPES_CHOICES, default=EXPENSE)
    amount = models.FloatField(_("Amount"))
    currency = models.CharField(_("Currency"), default=DEFAULT_CURRENCY, max_length=4)
    metadata = models.JSONField(
        verbose_name=_("Metadata"), blank=True, null=True, help_text=_("Metadata about transaction.")
    )
    link = models.ForeignKey(
        "self", verbose_name=_("Related transaction"), blank=True, null=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.date}: {self.amount} {self.currency} ({self.type})"

    def save(self, *args, **kwargs):
        if self.type == self.EXPENSE and self.amount > 0:
            self.amount = -abs(self.amount)

        super().save(*args, **kwargs)


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(_("Title"), max_length=255, null=True, blank=True)
    description = models.TextField(_("Description"), null=True, blank=True)
    metadata = models.JSONField(
        verbose_name=_("Metadata"), blank=True, null=True, help_text=_("Metadata about document.")
    )
    data = models.FileField(
        verbose_name=_("Data"),
        blank=True,
        null=True,
        upload_to="accounting",
        help_text=_("Upload proof of your work " "(document, video, image)."),
        validators=[
            FileExtensionValidator(["jpg", "jpeg", "png", "pdf", "doc", "docx", "txt", "xls", "xlsx"]),
            FileSizeValidator(MAX_FILE_SIZE_UPLOAD),
        ],
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="transactions",
        related_query_name="transaction",
        blank=True,
        null=True,
    )
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name="documents",
        related_query_name="document",
    )

    def __str__(self):
        name = ''

        if self.title:
            name = self.title
        elif self.invoice:
            name = _('Invoice')
        elif self.data:
            name = _('Document')

        return str(self.transaction) + " -> " + name

    def save(self, *args, **kwargs):
        if self.title == '' or self.title is None:
            if self.data:
                self.title = str(self.data)
            elif self.invoice:
                self.title = str(self.invoice)

        super().save(*args, **kwargs)
