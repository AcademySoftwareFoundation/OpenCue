### **High Level Overview**

The general flow of data starts from the RQD host, which sends status reports, known as host reports, to a cuebot on an interval. 
These host reports contain information about the host and signal if an RQD host is processing a job or available for a new one. 
This information is written to a database and is used by the cuebot to determine which pending jobs can be run on a host that is ready for a new job. 
The cuebot will query the database of pending jobs based on the specifications in the host report. 
The query will return jobs that can be processed by the RQD host, and the cuebot will dispatch this job to the RQD host that sent the host report.
In this configuration, the database is the source of truth for pending jobs.



### **Low Level Walkthrough of Dataflow**

#### RQD

- RQD creates status reports on an interval, which contains information about the host.
- These reports are collected from the RQD host in `rqmachine.py` and are assembled into a proto message in `rqnetwork.py` according to fields outlined in the `RqdReportStatusRequest` message found in `report.proto`
- A grpc network connection is established between the RQD and an instance of a Cuebot in the `__getChannel()` method in the `rqnetwork.py` file and the report is sent to the corresponding Cuebot

#### Cuebot

- Cuebot interfaces with the grpc connection using the `RqdReportStatic` class, which will send incoming host reports by calling `queueHostReport()` from the `HostReportHandler` class
- The `HostReportHandler` class will process the report by calling the `DispatchHandleHostReport` class, which wraps the report as an instance of the `DispatchHandleHostReport` class and adds it to the `HostReportQueue`, a thread pool that queues up the request, calling the `handleHostReport()` method when the task is ready to be executed
- The `handleHostReport()` method will log information about the host based on the incoming host report and will compare this information with the information stored about the available hosts. 
  If there are any discrepancies in the information, this method will create a new host based on the incoming host report. 
  Once the host has been verified, this method will  attempt to book a job to the host by creating a new `DispatchBookHost` instance to send to the `BookingQueue` class to execute
  - The `BookingQueue` uses the `HealthyThreadPool` class to prevent threads entering a deadlock
`HealthyThreadPool` extends the ThreadPoolExecutor class and monitors the state of the threads for signs of unhealthy thread and will shutdown if so.



- `DispatchBookHost` class wraps the host and a Dispatcher object as a command, and will attempt to book all resources either with dispatcher.dispatchHostToAllShows() or dispatcher.dispatchHost()
  - To dispatch a host, we first need to find jobs that are eligible to be run based on the paraments of the host
    - The dispatcher methods extend functionality from the `CoreUnitDispatcher`, the main class that deals with dispatching hosts for specific functions
    - The CoreUnitDispatcher uses the DispatchSupportService to find a set of  jobs that the given host can book.
      - This uses the `DispatcherDaoJdbc` to query the database using the `findDispatchJobs` or the `findDispatchJobsForAllShows` method
    - The `findDispatchJobs` method in the `DispatcherDaoJdbc` class gathers a list of bookable shows and checks for shows that are within their subscription limits and then queries the database using the FIND_JOBS_BY_SHOW query to return a list of jobs that fit the criteria and are pending in order of priority.
  - Once we have a job that is eligible, the CoreUnitDispatcher will call `dispatchJobs` with the host and the set of eligible jobs. 
    The method will loop through the list of available jobs and will check that the host still has available resources and will check if the job has a lock on it. 
    This lock is a cache that stores the id of jobs that should be skipped by for booking.
  - We then send the host and the job selected for dispatching to the `DispatchHost` method. Booking is skipped if the host has stranded cores or if the show is at/over burst
The frames within the job are then sent to the RQD via the `DispatchSupportService`, which contains an `RQDClient` to interact with the RQD gRPC.
    The list of procs that were dispatched are returned







### Database

- The database receives information about the incoming Host Reports and stores them
- The heart of the scheduling logic comes from the `FIND_JOBS_BY_SHOW` query in the `DispatchQuery` class
- The query will return a list of jobs that can be run given the current host resources and will rank the jobs in a priority queue
  - There is a mechanism to ensure that  resource-heavy jobs do not starve out smaller jobs in the priority queue
- The ranked list of jobs is then returned to the `CoreUnitDispatcher`
- `DisatchBookHost`, which uses `dispatcher.dispatchHostToAllShows()` or `dispatcher.dispatchHost()` to communicate with the RQD client and book the job

![plot](cuebot/src/main/java/com/imageworks/spcue/dispatcher/HandleHostReportSequenceDiagram.png)


### Issues with this Approach
This approach runs into issues with scalability and wasted computational resources. 
SPI currently has 3 cuebot servers, and thousands of RQD hosts. 
One RQD will connect to one cuebot via gRPC, as there is no load balancer in place. 

#### Database load 
The servers do not communicate between themselves, so the database is responsible for synchronizing the activity between the cuebot instances. 
The load on the database will increase as the number of cuebot instances  increase and the number of jobs increase, which may happen as SPI grows. 
Slowness at the query level slows the rate at which jobs are dispatched, slowing down the entire system. 
Furthermore, the code itself is not optimized. There are redundant database calls, contributing to the load on the database.

#### Redundant Job Booking

The current design allows a situation in which the same job can be booked to the same host.
For example, let there be two hosts, Host A and Host B that are available and can run Job A or Job  B. 
Ideally, the system would book Host A with either Job A or B, and Host B with the remaining job. 
However, there could be a situation in which both Host A and B are both booked with the same job. 
Since the cuebot instances are isolated from each other, a cuebot may query the database and find a pending job that is in the process of being booked and dispatched by another cuebot instance. 
This job will undergo the booking process on each cuebot only to fail at the dispatch stage for whichever cuebot was slowest. 
There is redundant effort, leading to wasted time and resources.

#### Unoptimized Threadpools

The current design uses multiple thread pools to manage the number of tasks, such as in the `HostReportQueue`, and the `BookingQueue`. 
These must all be manually configured at the moment, which can lead to inefficiency depending on the speed and amount of queries hitting the database. 
The implementation of the `HealthyThreadpool` allows for a mechanism of restarting threads in the event of a deadlock. 
Prior to this enhancement, threads would enter into a deadlock, causing the Cuebot servers to fail and necessitating a 2-hour restart cycle.


Main points of Concern 
 - Scaling due to reliance on reading list of available jobs from a complex database query
 - Wasted time and computational resources, as the job lock is only added at the end of the dispatch Jobs stage, ultimately resulting in additional database reads
 - Single point of failure, as the database is the source of truth and can't be distributed, 
   a reliable setup requires replicated databases with a sync mechanism, which is wasteful and potentially expensive. 
