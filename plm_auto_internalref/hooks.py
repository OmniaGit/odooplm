def set_manual_internal_references(env):
    """
    The templates whose internal reference is not the computed one keep it, and keep
    it editable: their auto_default_code is unset. Run when the module is installed
    and when it is updated to the version that brought the flag
    """
    templates = (
        env["product.template"]
        .with_context(active_test=False)
        .search([("engineering_code", "!=", False), ("engineering_code", "!=", "-")])
    )
    obj_pp = env["product.product"]
    manual_ids = [
        template.id
        for template in templates
        if template.default_code != obj_pp.computeDefaultCode({}, template)
    ]
    if manual_ids:
        env.cr.execute(
            "UPDATE product_template SET auto_default_code = FALSE WHERE id IN %s",
            (tuple(manual_ids),),
        )
        templates.invalidate_recordset(["auto_default_code"])


def post_init_hook(env):
    set_manual_internal_references(env)
