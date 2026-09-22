import importlib.util
from pathlib import Path
import unittest

path=Path(__file__).resolve().parents[1]/'skills/mistine-data-query/scripts/mistine_data_query.py'
spec=importlib.util.spec_from_file_location('client',path)
client=importlib.util.module_from_spec(spec);spec.loader.exec_module(client)

class DataContractTests(unittest.TestCase):
    def test_old_raw_material_total_rejected(self):
        result=client.normalize_result('weixin-materials',{'ok':True,'rows':[{'cost':200}]})
        self.assertFalse(result['ok']);self.assertNotIn('rows',result)

    def test_canonical_yuan_unchanged(self):
        result=client.normalize_result('weixin-materials',{'ok':True,'data_contract':{'version':'weixin-material-day-v1'},'rows':[{'cost':100.25,'net_roi':None}]})
        self.assertEqual(result['rows'][0]['cost'],100.25)
        self.assertIsNone(result['rows'][0]['net_roi'])

    def test_adq_real_account_rows_preserved_and_money_converted_once(self):
        result=client.normalize_result('adq-videos',{'ok':True,'rows':[{'account_id':'A','video_id':'same','cost':10000},{'account_id':'B','video_id':'same','cost':20000}]})
        self.assertEqual(len(result['rows']),2)
        self.assertEqual(sum(r['cost'] for r in result['rows']),300)

    def test_plan_source_not_mislabeled_material_contract(self):
        result=client.normalize_result('weixin-plan-materials',{'ok':True,'rows':[{'cost':40}]})
        self.assertTrue(result['ok']);self.assertNotIn('data_contract',result)

if __name__=='__main__':unittest.main(verbosity=2)
