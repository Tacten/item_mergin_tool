// Copyright (c) 2021, Aristo Roots and contributors
// For license information, please see license.txt

frappe.ui.form.on('Item Mergin Tool', {
	onload: function(frm) {
		frm.set_query("item_code", "items", function(frm) {
            return {
                filters: {
					has_batch_no:0
                }
            };
        });
		frm.set_query("warehouse", "items", function(frm,cdt,cdn) {
            let row=locals[cdt][cdn]
            return {
                filters: {
                    company:row.company
                }
            };
        });
	},
});