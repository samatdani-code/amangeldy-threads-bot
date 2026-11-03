import os
import tempfile
import unittest
from unittest.mock import patch
import main as b

class BotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'RAILWAY_VOLUME_MOUNT_PATH':self.tmp.name,
            'THREADS_ACCESS_TOKEN':'test','TELEGRAM_OWNER_ID':'123','THREADS_EXPECTED_USERNAME':'amangeldy.clinic'})
        self.env.start()
        b.init()
    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()
    def test_wrong_account(self):
        with patch.object(b,'threads',return_value={'id':'1','username':'other'}):
            with self.assertRaises(b.ServiceError): b.check()
        self.assertEqual(b.get('checked'),'')
    def test_pause_prevents_write(self):
        with patch.object(b,'threads') as api:
            b.publish({'id':1})
            api.assert_not_called()
    def test_similar_text(self):
        text='Запишите вопросы врачу заранее: в кабинете бывает сложно вспомнить всё.'
        with self.assertRaises(b.ServiceError):
            b.validate({'text':text},[{'text':text}])
    def test_uncertain_no_retry(self):
        pid=b.execute("INSERT INTO posts(text,rubric,scheduled,state) VALUES('text','test','slot','ready')")
        b.put('paused','0')
        p=b.rows('SELECT * FROM posts WHERE id=?',(pid,))[0]
        with patch.object(b,'check'), patch.object(b,'threads',side_effect=[{'id':'container'},b.ServiceError('timeout')]) as api, patch.object(b,'notify'):
            b.publish(p)
            b.publish(p)
            self.assertEqual(api.call_count,2)
        self.assertEqual(b.get('paused'),'1')
        self.assertEqual(b.rows('SELECT state FROM posts WHERE id=?',(pid,))[0]['state'],'uncertain')
    def test_claim_once(self):
        self.assertTrue(b.claim('slot'))
        self.assertFalse(b.claim('slot'))
    def test_no_delete_without_confirmation(self):
        with patch.object(b,'threads') as api, patch.object(b,'send'):
            b.handle({'from':{'id':123},'chat':{'id':123},'text':'/confirm_delete 1'})
            api.assert_not_called()
    def test_unauthorized(self):
        with patch.object(b,'put') as write:
            b.handle({'from':{'id':999},'chat':{'id':999},'text':'/resume'})
            write.assert_not_called()

if __name__=='__main__': unittest.main()
