from queue import Queue
import threading
import time
import mlperf_loadgen
import numpy

class ImplementationException (Exception):
    def __init__(self, msg):
        self.msg = msg

    def __repr__(self):
        return "ImplementationException: {}".format(self.msg)

def process_latencies(latencies_us):
    print("Average latency: ")
    print(numpy.mean(latencies_us))
    print("Median latency: ")
    print(numpy.percentile(latencies_us, 50))
    print("90 percentile latency: ")
    print(numpy.percentile(latencies_us, 90))

class Task:
    def __init__(self, query_id, sample_id):
        self.query_id = query_id
        self.sample_id = sample_id

class Runner:
    
    def __init__(self, qSize=5):
        self.tasks = Queue(maxsize=qSize)

    def load_samples_to_ram(self, query_samples):
        return

    def unload_samples_from_ram(self, query_samples):
        return

    ##
    # @brief Invoke process a task
    def process(self, qitem):
        raise ImplementationException("Please implement Process function")

    ##
    # @brief infinite loop that pulls translation tasks from a queue
    # @note This needs to be run by a worker thread
    def handle_tasks(self):
        while True:
            # Block until an item becomes available
            qitem = self.tasks.get(block=True)

            # When a "None" item was added, it is a 
            # signal from the parent to indicate we should stop
            # working (see finish)
            if qitem is None:
                break

            result = self.process(qitem)
            response = []

            # TBD: do something when we are running accuracy mode
            # We need to properly store the result. Perhaps through QuerySampleResponse, otherwise internally
            # in this instance of Runner.
            # QuerySampleResponse contains an ID, a size field and a data pointer field
            response.append(mlperf_loadgen.QuerySampleResponse(qitem.query_id, 0, 0))
            mlperf_loadgen.QuerySamplesComplete(response)
    
    ##
    # @brief Stop worker thread
    def finish(self):
        print("empty queue")
        self.tasks.put(None)
        self.worker.join()

    ##
    # @brief function to handle incomming querries, by placing them on the task queue
    # @note a query has the following fields:
    # * index: this is the sample_ID, and indexes in e.g., an image or sentence.
    # * id: this is the query ID
    def enqueue(self, query_samples):
        raise ImplementationException("Please implement Enqueue function")

    ##
    # @brief start worker thread
    def start_worker(self):
        self.worker = threading.Thread(target=self.handle_tasks)
        self.worker.daemon = True
        self.worker.start()

class DummyRunner (Runner):
    def __init__(self):
        Runner.__init__(self)
        self.count = 0

    def enqueue(self, query_samples):
        for sample in query_samples:
            print("Adding Dummy task to the queue.")
            task = Task(sample.id, sample.index)
            self.tasks.put(task)

    def process(self, qitem):
        print("Default dummy process, processing the {}'th query for sample ID {}.".format(self.count, qitem.sample_id))
        self.count += 1
        
        return self.count

if __name__ == "__main__":
    runner = DummyRunner()

    runner.start_worker()

    settings = mlperf_loadgen.TestSettings()
    settings.scenario = mlperf_loadgen.TestScenario.SingleStream
    settings.mode = mlperf_loadgen.TestMode.PerformanceOnly
    settings.samples_per_query = 1
    settings.target_qps = 10        # Doesn't seem to have an effect
    settings.target_latency_ns = 1000000000

    
    total_queries = 256 # Maximum sample ID + 1
    perf_queries = 8   # TBD: Doesn't seem to have an effect

    sut = mlperf_loadgen.ConstructSUT(runner.enqueue, process_latencies)
    qsl = mlperf_loadgen.ConstructQSL(
        total_queries, perf_queries, runner.load_samples_to_ram, runner.unload_samples_from_ram)
    mlperf_loadgen.StartTest(sut, qsl, settings)
    mlperf_loadgen.DestroyQSL(qsl)
    mlperf_loadgen.DestroySUT(sut)

