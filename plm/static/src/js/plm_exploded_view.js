odoo.define('plm.plm_exploded_view', function (require) {
'use strict';

var ajax = require('web.ajax');
var ControlPanelMixin = require('web.ControlPanelMixin');
var Context = require('web.Context');
var core = require('web.core');
var data = require('web.data');
var pyeval = require('web.pyeval');
var SearchView = require('web.SearchView');
var session = require('web.session');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

var PlmExplodedWidget = Widget.extend(ControlPanelMixin, {
	title: core._t('Exploded View'),
    template: 'plm_exploded_view',
	events: {
        "click .o_plm_entity_open": '_onRedirect',
    },
    init: function(parent, action, options) {
    	this._active_id= arguments[1].context.active_id;
    	if (this._active_id==null){
    		this._active_id = action.params.active_id;}
        this.actionManager = parent;
        this.action = action;
        this.domain = [];
        return this._super.apply(this, arguments);
    },
    start: function(){
        var self = this;
        return $.when(function(){
            this._super();
            var status = {
                breadcrumbs: self.action_manager.get_breadcrumbs(),
                cp_content: {$buttons: self.$buttons},
            };
            self.update_control_panel(status);
        });
    },
    willStart: function () {
        var self = this;
        var def = [];
        if(this._active_id){
        	self.res=[]
        	var def = this._rpc({
        		model: 'product.product',
        		method: 'getParentBomStructure',
        		context: {'id': this._active_id},
        		}).then(function(res) {
        	self.res=res
        });
        }
        return $.when(this._super.apply(this, arguments), def);
    },
 
    _onRedirect: function (event) {
        event.preventDefault();
        var $target = $(event.target);
        this.do_action({
            type: 'ir.actions.act_window',
            view_type: 'form',
            view_mode: 'form',
            res_model: 'product.product',
            views: [[false, 'form']],
            res_id: $target.data('product-id'),
        });
    },
});

core.action_registry.add('plm_exploded_view', PlmExplodedWidget);

});
