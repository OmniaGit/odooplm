PLM Auto Translator
===================

Automatically translates Odoo ``.po`` language files using Google Translate,
filling in empty translation strings on a configurable schedule.

Overview
--------

Maintaining translations for large Odoo installations is time-consuming. This
module introduces the **Auto Translator** model which monitors one or more
filesystem paths for ``.po`` files and automatically translates any untranslated
entries (``msgstr`` is empty) into the configured target languages. It uses the
``googletrans`` library and is designed to run as a scheduled action.

Key Features
------------

* Configurable translation jobs: each record specifies a filesystem path and
  a list of target languages
* Only fills in empty ``msgstr`` entries — existing translations are not
  overwritten
* Constraint prevents duplicate language assignments for the same path
* Designed to run as a recurring scheduled action (``run_daily_translation``)
* Uses ``polib`` for ``.po`` file parsing and writing

Installation
------------

Requires ``googletrans`` and ``polib`` Python packages::

    pip install googletrans==4.0.0rc1 polib

Dependencies
------------

* ``plm`` — OdooPLM core module
