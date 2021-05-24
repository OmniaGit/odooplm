odoo.define('activity_validation.systray.ActivityMenu', function (require) {
"use strict";

var session = require('web.session');

var ActivityMenuH = require('mail.systray.ActivityMenu');

ActivityMenuH.include({
    /**
     * Redirect to particular model view
     * @private
     * @param {MouseEvent} event
     */
    _onActivityFilterClick: function (event) {
        // fetch the data from the button otherwise fetch the ones from the parent (.o_mail_preview).
        var data = _.extend({}, $(event.currentTarget).data(), $(event.target).data());
        var context = {};
        if (data.filter === 'my') {
            context['search_default_activities_overdue'] = 1;
            context['search_default_activities_today'] = 1;
        } else {
            context['search_default_activities_' + data.filter] = 1;
        }
        // Necessary because activity_ids of mail.activity.mixin has auto_join
        // So, duplicates are faking the count and "Load more" doesn't show up
        context['force_search_count'] = 1;
		context['from_activity_counter'] = 1;
        this.do_action({
            type: 'ir.actions.act_window',
            name: data.model_name,
            res_model:  data.res_model,
            views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
            search_view_id: [false],
            domain: [['activity_user_id', '=', session.uid]],
            context:context,
        });
    },
});

});