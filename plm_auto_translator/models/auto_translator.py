# -*- coding: utf-8 -*-

import os
import polib
import logging
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from googletrans import Translator

_logger = logging.getLogger(__name__)


class AutoTranslator(models.Model):
    _name = "auto.translator"
    _description = "Automatic PO Translator"
    _rec_name = "name"

    name = fields.Char(string="Name", required=True)
    path = fields.Char(
        string="Custom Path",
    )
    lang_ids = fields.Many2many("res.lang", string="Translate To Languages")

    @api.constrains("path", "lang_ids")
    def _check_duplicate_languages_per_path(self):
        """Prevent assigning the same base language to the same path multiple times."""
        for record in self:
            existing = self.search(
                [
                    ("id", "!=", record.id),
                    ("path", "=", record.path),
                ]
            )
            configured_langs = set()
            for cfg in existing:
                configured_langs.update(
                    lang.code.split("_")[0] for lang in cfg.lang_ids
                )

            current_langs = set(lang.code.split("_")[0] for lang in record.lang_ids)
            duplicates = current_langs & configured_langs
            if duplicates:
                dup_names = ", ".join(duplicates)
                raise ValidationError(
                    f"Language(s) already configured for this path: {dup_names}"
                )

    @api.model
    def translate_text(self, text, src_lang="en", dest_lang="de"):
        """Translate a single text string from src_lang to dest_lang using Google Translate."""
        try:
            translator = Translator()
            result = translator.translate(text, src=src_lang, dest=dest_lang)
            return result.text
        except Exception as e:
            _logger.warning(f"Translation failed for '{text}': {e}")
            return text

    @api.model
    def translate_po_file(self, filepath, src_lang="en", dest_lang="de"):
        """Translate entries in a .po file that have empty msgstr values."""
        po = polib.pofile(filepath)
        changed = False

        for entry in po:
            if entry.msgstr.strip() == "" and entry.msgid.strip() != "":
                translated = self.translate_text(entry.msgid, src_lang, dest_lang)
                if translated and translated != entry.msgid:
                    entry.msgstr = translated
                    changed = True

        if changed:
            po.save(filepath)
            _logger.info(f"Updated translations saved in {filepath}")

    def run_daily_translation(self):
        """Run translation on all configured paths and languages. Intended to be used as a scheduled action."""
        for record in self.search([]):
            _logger.info(f"Running translation for: {record.name}")

            if not os.path.exists(record.path):
                _logger.warning(f"Path does not exist: {record.path}")
                continue

            for lang in record.lang_ids:
                lang_code = lang.code or ""
                possible_po_files = [f"{lang_code}.po", f"{lang_code.split('_')[0]}.po"]

                found_file = False

                for root, dirs, files in os.walk(record.path):
                    for file in files:
                        if file in possible_po_files:
                            filepath = os.path.join(root, file)
                            dest_lang = lang_code.split("_")[
                                0
                            ]  # e.g. 'ja' for Google Translate
                            try:
                                _logger.info(f"Translating: {filepath} → {dest_lang}")
                                self.translate_po_file(filepath, dest_lang=dest_lang)
                                found_file = True
                            except Exception as e:
                                _logger.error(f"Error translating {filepath}: {e}")

                if not found_file:
                    _logger.warning(f"No .po file found for language: {lang_code}")
