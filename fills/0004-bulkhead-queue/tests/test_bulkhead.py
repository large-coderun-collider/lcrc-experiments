import unittest
from lcrc_bulkhead.bulkhead import AdmissionResult, Bulkhead, BulkheadFullError


class TestBulkhead(unittest.TestCase):
    def test_initial_state(self):
        bh = Bulkhead(max_concurrent=2, max_queue=2)
        snap = bh.snapshot()
        self.assertEqual(snap.active_count, 0)
        self.assertEqual(snap.queue_count, 0)

    def test_acquire_and_queue_saturation(self):
        bh = Bulkhead(max_concurrent=1, max_queue=1)
        
        # 1. Fill active slot
        self.assertEqual(bh.try_acquire(), AdmissionResult.ACCEPTED)
        
        # 2. Fill queue slot
        self.assertEqual(bh.try_acquire(), AdmissionResult.QUEUED)
        bh._queue.append(lambda: None)  # simulate storing queued work
        
        # 3. Saturated -> Reject
        self.assertEqual(bh.try_acquire(), AdmissionResult.REJECTED)

    def test_release_promotes_queued_task(self):
        bh = Bulkhead(max_concurrent=1, max_queue=1)
        bh.try_acquire()
        bh.try_acquire()
        
        dummy_task = lambda: "queued_work"
        bh._queue.append(dummy_task)
        
        # Releasing active slot should promote the queued task to active
        promoted = bh.release()
        self.assertIs(promoted, dummy_task)
        self.assertEqual(bh.snapshot().active_count, 1)
        self.assertEqual(bh.snapshot().queue_count, 0)

    def test_submit_success(self):
        bh = Bulkhead(max_concurrent=1, max_queue=1)
        executed = False

        def work():
            nonlocal executed
            executed = True

        res = bh.submit(work)
        self.assertEqual(res, AdmissionResult.ACCEPTED)
        self.assertTrue(executed)
        # Should automatically release after work completes
        self.assertEqual(bh.snapshot().active_count, 0)

    def test_submit_full_error(self):
        bh = Bulkhead(max_concurrent=1, max_queue=0)
        bh.try_acquire()  # occupy the only slot

        with self.assertRaises(BulkheadFullError):
            bh.submit(lambda: None)


if __name__ == "__main__":
    unittest.main()