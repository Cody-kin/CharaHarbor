import copy,json,unittest
from datetime import datetime,timezone,timedelta
from companion.public_search import question,request,parse,SearchRefused,PRICE_REVIEWED,safe_source


class SearchTests(unittest.TestCase):
    def response(self):
        return dict(model='gpt-6.1-terra',status='completed',error=None,usage=dict(input_tokens=100,output_tokens=40),output=[
            dict(type='web_search_call',status='completed'),dict(type='message',role='assistant',status='completed',content=[dict(type='output_text',text='公开资料说明。',annotations=[dict(type='url_citation',url='https://bang-dream.com/news/1',start_index=0,end_index=6)])])])
    def test_minimal_queries_not_private_context(self):
        self.assertEqual(question('查一下小睦最新活动')['query'],'Ave Mujica latest official announcements and publicly documented facts')
        self.assertIsNone(question('我家地址123456，查一下小睦'))
        self.assertIn('clarify',question('我这里天气怎样'))
        self.assertIn('Tokyo',question('你那边天气怎样',role_city='东京')['query'])
        self.assertIsNone(question('你好，我喜欢绿茶'))
    def test_single_tool_no_history_or_auto_retry(self):
        body=request('Ave Mujica latest official news',['bang-dream.com'],PRICE_REVIEWED)
        self.assertEqual(body['max_tool_calls'],1);self.assertFalse(body['store']);self.assertEqual(body['reasoning']['effort'],'none')
        self.assertNotIn('previous_response_id',body);self.assertNotIn('conversation',body)
        with self.assertRaisesRegex(SearchRefused,'price'):request('public topic',['bang-dream.com'],PRICE_REVIEWED+timedelta(days=8))
    def test_sources_usage_and_cost(self):
        result=parse(json.dumps(self.response()).encode(),['bang-dream.com'],PRICE_REVIEWED)
        self.assertEqual(result['booked_micros'],20600);self.assertEqual(result['search_calls'],1)
        self.assertEqual(result['sources'],['https://bang-dream.com/news/1'])
    def test_missing_foreign_or_private_source_rejected(self):
        for url in ('https://evil.example/news','https://bang-dream.com.evil.example','http://bang-dream.com/news','https://127.0.0.1/a'):
            response=self.response();response['output'][1]['content'][0]['annotations'][0]['url']=url
            with self.assertRaises(SearchRefused):parse(json.dumps(response).encode(),['bang-dream.com'])
    def test_unknown_usage_multiple_calls_incomplete_rejected(self):
        response=self.response();response['usage']['input_tokens']=200000
        with self.assertRaises(SearchRefused):parse(json.dumps(response).encode(),['bang-dream.com'])
        response=self.response();response['output'].append(dict(type='web_search_call',status='completed'))
        with self.assertRaises(SearchRefused):parse(json.dumps(response).encode(),['bang-dream.com'])
        response=self.response();response['status']='incomplete'
        with self.assertRaises(SearchRefused):parse(json.dumps(response).encode(),['bang-dream.com'])
