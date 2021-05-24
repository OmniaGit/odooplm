odoo.define('plm.ProductKanbanRecord', function (require) {
"use strict";

var KanbanRecord = require('web.KanbanRecord');

var view_registry = require('web.view_registry');
var core = require('web.core');

var onHoverIn = function(){
	var el = $(this);
	var elTop  = el.offset().top;
	var elLeft  = el.offset().left;
	var a =  $(document).width() / 2;
	var b = $(document).height() /2;
    if(elLeft< a){
    	if(elTop<b){el.css({"transform-origin": "0% 0%"});}
    	else{el.css({"transform-origin": "0% 100%"});}
    }else{
    	if(elTop<b){el.css({"transform-origin": "100% 0%"});}
    	else{el.css({"transform-origin": "100% 100%"});}	
    }
};

var onHoverOut = function(){}

var PlmKanbanRecord = KanbanRecord.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
	_render: function () {
	    var self = this;
	    return this._super.apply(this, arguments).then(function () {
	    	var images = self.$el.find('img.image_component_kanban');
	    	if(images){
		    	$.each(images, function(i, val){
		    		$(val).hover(onHoverIn);
		    	});
	    	}
	    });
	},	
});

return PlmKanbanRecord;

});
