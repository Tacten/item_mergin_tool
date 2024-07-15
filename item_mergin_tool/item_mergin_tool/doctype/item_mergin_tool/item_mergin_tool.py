# -*- coding: utf-8 -*-
# Copyright (c) 2021, Aristo Roots and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import random
from frappe.model.document import Document
from frappe import copy_doc
from frappe.model.rename_doc import rename_doc
from frappe.utils.background_jobs import enqueue
import string


class ItemMerginTool(Document):
    def on_submit(self):
        enqueue(self.repack_and_merged_item, job_name=f'This item has been queued',queue='long')
        frappe.msgprint(f'Your request has been queued')

    def repack_and_merged_item(self):
        items={}
        sufix={}
        for row in self.items:
            old_doc=frappe.get_doc('Item',row.item_code)
            rand=self.id_generator()
            name= old_doc.item_code
            bin_filter={
                'item_code': row.item_code,
                'warehouse':row.warehouse,
            }
            valuation_rate = frappe.db.get_value('Bin', bin_filter, 'valuation_rate')
            actual_qty = frappe.db.get_value('Bin', bin_filter, 'actual_qty')
            
            if old_doc.valuation_rate is None or old_doc.valuation_rate == 0:
                self.add_comment(text = f'Skipping: Item {row.item_code} valuation rate must be greater than 1 ')
                continue
            
            if actual_qty is None or actual_qty == 0:
                self.add_comment(text = f'Skipping: Item {row.item_code} doesnot have any quantity')
                continue
            
            if old_doc.default_bom:
                frappe.db.set_value('BOM', old_doc.default_bom, {
                    'item':row.item_code+rand
                })
            #creating new Item
            
            if row.item_code not in items:
                
                new_doc = copy_doc(old_doc, ignore_no_copy=True)
                new_doc.item_code=row.item_code+rand
                new_doc.item_name=old_doc.item_name+rand
                new_doc.valuation_rate=old_doc.valuation_rate
                new_doc.has_batch_no=1
                new_doc.create_new_batch=1
                new_doc.batch_number_series=row.batch_series
                new_doc.save()
                items[name]=row.batch_series
                sufix[name]=rand
            else:
                rand=sufix[name]
            
            self.add_comment(text = f'Item {row.item_code} with {row.warehouse} is under process')
            company_doc=frappe.get_doc('Company',row.company)
            #Creating Stock Entry
            stock_entry=frappe.get_doc({
                    'doctype': 'Stock Entry',
                    'stock_entry_type': 'Repack',
                    'company':row.company,
                    'project': row.project,
                    'remarks':'Repack Entry for <b>{0}</b> to <b>{1}</b> '.format(row.item_code,row.item_code+rand)
                })
            stock_entry.append('items',{
                'item_code':row.item_code,
                's_warehouse':row.warehouse,
                'qty':actual_qty,
                'cost_center':company_doc.cost_center,
                'valuation_rate':valuation_rate,
                'project':row.project
            })
            stock_entry.append('items',{
                'item_code':row.item_code+rand,
                't_warehouse':row.warehouse,
                'qty':actual_qty,
                'cost_center':company_doc.cost_center,
                'valuation_rate':valuation_rate,
                'project':row.project
            })
            stock_entry.save()
            stock_entry.submit()
            self.add_comment(text = f'Stock Entry Repack has been created for {row.item_code} and {row.warehouse}')

        for row,suf in zip(items,sufix):

            frappe.db.set_value('Item', row, {
                'has_batch_no': 1,
                'create_new_batch': 1,
                'batch_number_series':items[row]
            })
            rename_doc('Item',row+sufix[suf],row,merge=True)

    def id_generator(size=2, chars=string.ascii_uppercase + string.digits):
        return ''+random.choice(chars)