package main

import (
	"os"
	"sync"
	"time"

	"github.com/hyperledger-labs/mirbft/checkpoint"
	"github.com/hyperledger-labs/mirbft/config"
	"github.com/hyperledger-labs/mirbft/crypto"
	"github.com/hyperledger-labs/mirbft/discovery"
	"github.com/hyperledger-labs/mirbft/manager"
	"github.com/hyperledger-labs/mirbft/membership"
	"github.com/hyperledger-labs/mirbft/messenger"
	"github.com/hyperledger-labs/mirbft/orderer"
	"github.com/hyperledger-labs/mirbft/profiling"
	"github.com/hyperledger-labs/mirbft/request"
	"github.com/hyperledger-labs/mirbft/statetransfer"
	"github.com/hyperledger-labs/mirbft/tracing"
	"github.com/rs/zerolog"
	logger "github.com/rs/zerolog/log"
)

// Flag indicating whether profiling is enabled.
// Used to decide whether the tracer should shut down the process on the INT signal or not.
// TODO: This is ugly and dirty. Implement graceful shutdown!
var profilingEnabled = false

type linkedList struct {
	requests, throughput int32
	pre, nxt             *linkedList
}

var statistics [4]linkedList
var msg_lock sync.Mutex

const (
	trainer_addr = "localhost:32767"
)

func main() {

	// Get command line arguments
	configFileName := os.Args[1]
	discoveryServAddr := os.Args[2]
	ownPublicIP := os.Args[3]
	ownPrivateIP := os.Args[4]

	config.LoadFile(configFileName)

	// Configure logger
	zerolog.SetGlobalLevel(config.Config.LoggingLevel)
	zerolog.TimeFieldFormat = zerolog.TimeFormatUnixMicro
	logger.Logger = logger.Output(zerolog.ConsoleWriter{
		Out:        os.Stdout,
		NoColor:    true,
		TimeFormat: "15:04:05.000"})
	//zerolog.TimeFieldFormat = zerolog.TimeFormatUnixMs
	//logger.Logger = logger.Output(zerolog.ConsoleWriter{
	//	Out:        os.Stdout,
	//	NoColor:    true,
	//	TimeFormat: "15:04:05.000",
	//})

	// Initialize packages that need the configuration to be loaded for initialization
	membership.Init()
	request.Init()
	tracing.Init()
	statetransfer.Init()

	// Register with the discovery service and obtain:
	// - Own ID
	// - Identities of all other peers
	// - Private key
	// - Public key for BLS threshold cryptosystem
	// - Private key share for BLS threshold cryptosystem
	ownID, nodeIdentities, privateKey, serializedTBLSPubKey, serializedTBLSPrivKeyShare :=
		discovery.RegisterPeer(discoveryServAddr, ownPublicIP, ownPrivateIP)
	membership.OwnID = ownID
	membership.OwnPrivKey = privateKey
	membership.InitNodeIdentities(nodeIdentities)
	logger.Info().
		Int32("ownID", ownID).
		Int("numPeers", len(nodeIdentities)).
		Msg("Registered with discovery server.")

	// Desirialize TBLS keys
	TBLSPubKey, err := crypto.TBLSPubKeyFromBytes(serializedTBLSPubKey)
	if err != nil {
		logger.Fatal().Msgf("Could not deserialize TBLS public key %s", err.Error())
	}
	membership.TBLSPublicKey = TBLSPubKey
	TBLSPrivKeyShare, err := crypto.TBLSPrivKeyShareFromBytes(serializedTBLSPrivKeyShare)
	if err != nil {
		logger.Fatal().Msgf("Could not deserialize TBLS private key share %s", err.Error())
	}
	membership.TBLSPrivKeyShare = TBLSPrivKeyShare

	// Start profiler if necessary
	// ATTENTION! We first look for argument 6, and only then check argument 5
	//            (as the presence of profiling influences setting up of tracing).
	if len(os.Args) > 6 {
		profilingEnabled = true // UGLY DIRTY CODE!
		logger.Info().Msg("Profiling enabled.")
		setUpProfiling(os.Args[6])
	}

	// Set up tracing if necessary
	if len(os.Args) > 5 {
		setUpTracing(os.Args[5], ownID)
	}

	// Set up monitering CPU
	// profiling.MonitorCPU(ownID)

	// Declare variables for component modules.
	var mngr manager.Manager
	var ord orderer.Orderer
	var chkp checkpoint.Checkpointer
	var rsp *request.Responder

	// Instantiate component modules (with stubs).

	mngr = setManager(config.Config.Manager)
	// mm := mngr.(*manager.MirManager)
	ord = setOrderer(config.Config.Orderer)
	chkp = setCheckpointer(config.Config.Checkpointer)
	rsp = request.NewResponder()

	// Initialize modules.
	// No outgoing messages must be produced even after initialization,
	// but the modules must be raady to process incoming messages.
	ord.Init(mngr)
	chkp.Init(mngr)

	//// Make adjustments if this peer simulates a faulty one
	//if membership.OwnID < int32(config.Config.Failures) {
	//	config.Config.ViewChangeTimeout = 100
	//}

	// Register message and entry handlers
	messenger.CheckpointMsgHandler = chkp.HandleMessage
	messenger.OrdererMsgHandler = ord.HandleMessage
	messenger.ClientRequestHandler = request.HandleRequest
	messenger.StateTransferMsgHandler = statetransfer.HandleMessage
	statetransfer.OrdererEntryHandler = ord.HandleEntry

	// Create wait group for all the modules that will run as separate goroutines.
	// (Currently the graceful termination is not implemented, so waiting on wg will take forever and the process
	// needs to be killed.)
	wg := sync.WaitGroup{}
	wg.Add(5) // messenger, checkpointer, orderer, manager, responder

	// Start the messaging subsystem.
	// Connect needs to come after starting the messenger which launches the gRPC server everybody connects to.
	// Otherwise we deadlock, everybody connecting to gRPC servers that are not (and never will be) running.
	go messenger.Start(&wg)
	messenger.Connect()
	logger.Info().Msg("Connected to all peers.")

	// Synchronize with master again to make sure that all peers finished connecting.
	discovery.SyncPeer(discoveryServAddr, ownID)
	logger.Info().Msg("All peers finished connecting. Starting ISS.")

	// If we are simulating a crashed node, exit immediately.
	if config.Config.LeaderPolicy == "SimulatedRandomFailures" {
		crash := true
		for _, l := range manager.NewLeaderPolicy(config.Config.LeaderPolicy).GetLeaders(0) {
			if l == membership.OwnID {
				crash = false
			}
		}
		if crash {
			logger.Info().Msg("Simulating crashed peer. Exiting.")
			return
		}
	}

	// Start all modules.
	// The order of the calls must not matter, as they are all concurrent. If it does, it's a bug.
	// By now all the modules must be initialized and ready to process messages.
	// After starting, the modules will produce messages on their own.
	go rsp.Start(&wg)
	go chkp.Start(&wg)
	go mngr.Start(&wg)
	go ord.Start(&wg)
	config.EpochStartTime = time.Now().UnixMilli()

	/*
		// set up a GRPC connection.
		logger.Info().Msg("Try to set up a GRPC connection.")

		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()

			conn, err := grpc.DialContext(ctx, trainer_addr, grpc.WithInsecure(), grpc.WithBlock())
			if err != nil {
				// log.Fatalf("did not connect: %v", err)
				logger.Error().Err(err).Msg("cannot set up the gRPC connection.")
			} else {
				c := pb.NewMetricsServiceClient(conn) // try to connect to the trainer
				response, err := c.Connect(context.Background(), &pb.Timestamp{
					Timestamp: time.Now().UnixNano(),
				})
				response.Timestamp += 1
				if err != nil {
					logger.Error().Err(err).Msg("cannot connect.")
				}
					start_time := response.GetTimestamp()
					// start_time := time.Now().UnixNano() + 5000000000

					// send latency, throughput, workload, BS, BT, Leader to agent
					// and modify the config by the output of RL agent every 20s
					// use rule-based method to modify the config every 1s
					file, _ := os.OpenFile(fmt.Sprintf("../../../train/state%d.txt", ownID), os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0777)

					// wait until the harmonization time to start
					total_count, now_rule, next_rule := 0, int64(0), start_time-1000000000
					now_RL, next_RL := int64(0), start_time+500000000
					flag, lastD, lastR := true, int64(0), int64(0)
					Requests, binary, Smax, lastThr := 0, 0, 0, 0
					msg := &pb.MetricsRequest{}

					for i := 0; i < 4; i++ {
						if i > 0 {
							statistics[i].pre = &statistics[i-1]
						} else {
							statistics[i].pre = &statistics[3]
						}
						if i < 3 {
							statistics[i].nxt = &statistics[i+1]
						} else {
							statistics[i].nxt = &statistics[0]
						}
					}
					sta_pointer, MTP, enough, avg_requests, avg_throughput := &statistics[0], 1, false, int32(0), int32(0)
					// MTP = MTP * 2 / 2

					go func() {
						for {
							now_RL, next_RL = time.Now().UnixNano(), next_RL+int64(MTP)*1000000000
							if now_RL < next_RL {
								time.Sleep(time.Duration((next_RL-now_RL)/1000) * time.Microsecond)
							}
							logger.Info().Int64("timestamp", time.Now().UnixNano()).Msg("send metrics to agent.")
							msg_lock.Lock()
							tmp_msg := msg
							msg = &pb.MetricsRequest{}
							msg_lock.Unlock()
							response, err := c.SendMetrics(context.Background(), tmp_msg)
							if err != nil {
								logger.Fatal().Err(err).Msg("cannot send metrics.")
							}
							logger.Info().Int64("timestamp", time.Now().UnixNano()).Msg("receive response and modify the config")
							config.Config.BatchSize = int(response.GetBatchSize())
							config.Config.BatchTimeoutMs = int(response.GetBatchTimeout())
							config.Config.BatchTimeout = time.Duration(config.Config.BatchTimeoutMs) * time.Millisecond
						}
					}()

					go func() {
						for {
							now_rule, next_rule = time.Now().UnixNano(), next_rule+int64(1)*1000000000
							if now_rule < next_rule {
								time.Sleep(time.Duration((next_rule-now_rule)/1000) * time.Microsecond)
							}
							latency, throughput := int32(1000), int32(0)
							if config.CommittedRequests[ownID] > int64(lastR) {
								latency = int32((config.TotalDelay[ownID] - lastD) / int64(1e6) / (config.CommittedRequests[ownID] - lastR))
								throughput = int32(config.CommittedRequests[ownID] - lastR)
							}
							if flag {
								flag, lastD, lastR = false, config.TotalDelay[ownID], config.CommittedRequests[ownID]
								total_count, config.TotalRequests, config.TotalPayload = total_count+1, 0, 0
								continue
							}
							lastD, lastR = config.TotalDelay[ownID], config.CommittedRequests[ownID]
							TotalRequests, TotalPayload := config.TotalRequests, config.TotalPayload
							total_count, config.TotalRequests, config.TotalPayload = total_count+1, 0, 0

							logger.Info().
								Int32("times", int32(total_count)).
								Int64("timestamp", time.Now().UnixNano()).
								Int("batchsize", config.Config.BatchSize).
								Msg("collect metrics.")
							file.WriteString(fmt.Sprintf("%8d\t%8d\t%8d\t%10d\t%8d\t%8d\t%8d\n", throughput, latency, TotalRequests, TotalPayload, config.Config.BatchSize, config.Config.BatchTimeoutMs, mm.GETLEADERS()[0]))

							msg_lock.Lock()
							msg.Throughput = append(msg.Throughput, throughput)
							msg.Latency = append(msg.Latency, latency)
							msg.Requests = append(msg.Requests, int32(TotalRequests))
							msg.RequestsSize = append(msg.RequestsSize, int32(TotalPayload))
							msg.BatchSize = append(msg.BatchSize, int32(config.Config.BatchSize))
							msg.BatchTimeout = append(msg.BatchTimeout, int32(config.Config.BatchTimeoutMs))
							msg.Leader = append(msg.Leader, mm.GETLEADERS()[0])
							if ownID != msg.Leader[len(msg.Leader)-1] {
								msg.Leader[len(msg.Leader)-1] = msg.Leader[len(msg.Leader)-1] * 100
							} else {
								msg.Leader[len(msg.Leader)-1] = msg.Leader[len(msg.Leader)-1]*100 + 1
							}
							msg_lock.Unlock()

							if ownID != msg.Leader[len(msg.Leader)-1]/100 {
								continue
							}

							if !enough {
								avg_requests = avg_requests + int32(TotalRequests)
								avg_throughput = avg_throughput + throughput
								sta_pointer.requests = int32(TotalRequests)
								sta_pointer.throughput = throughput
								sta_pointer = sta_pointer.nxt
								if sta_pointer == &statistics[0] {
									enough = false
								}
							} else {
								Requests = int(avg_requests)
								avg_requests = avg_requests - sta_pointer.requests + int32(TotalRequests)
								avg_throughput = avg_throughput - sta_pointer.throughput + throughput
								sta_pointer.requests = int32(TotalRequests)
								sta_pointer.throughput = throughput
								sta_pointer = sta_pointer.nxt
								logger.Info().Int("Req", int(avg_requests)).Int("Throughput", int(avg_throughput)).Msg("Req and Thr.")
								if Requests == 0 {
									continue
								}
								if avg_throughput*21 >= avg_requests*20 {
									binary, lastThr = 0, 0
								} else {
									logger.Info().Int("Req", int(avg_requests)).Int("Throughput", int(avg_throughput)).Msg("Try to change batchsize.")
									if binary == 0 {
										binary = config.Config.BatchSize
										config.Config.BatchSize = config.Config.BatchSize * int(avg_requests) / Requests
										logger.Info().
											Int("Req_old", int(Requests)).
											Int("Req_now", int(avg_requests)).
											Int("batchsize_old", binary).
											Int("batchsize_new", config.Config.BatchSize).
											Msg("calculate the new batchsize.")
										if config.Config.BatchSize > binary {
											Smax = Min(config.Config.BatchSize-binary, 500)
										} else {
											Smax = Max(config.Config.BatchSize-binary, -500)
										}
									} else if lastThr == 0 {
										lastThr = int(avg_throughput)
										config.Config.BatchSize = binary + Smax
									} else {
										if avg_throughput*20 <= int32(lastThr)*19 {
											Smax /= 2
										} else if avg_throughput*20 <= int32(lastThr)*21 {
											binary, lastThr = 0, 0
										} else {
											lastThr = int(avg_throughput)
											binary = config.Config.BatchSize
										}
										config.Config.BatchSize = binary + Smax
									}
								}
								if config.Config.BatchSize <= 100 {
									config.Config.BatchSize = 100
									// binary = 0
								} else if config.Config.BatchSize >= 5000 {
									config.Config.BatchSize = 5000
									// binary = 0
								}
							}
						}
					}()
			}

			defer conn.Close()
	*/

	// Wait for all modules to finish.
	wg.Wait()
}

// Enables and starts the profiler of used resources.
func setUpProfiling(outFilePrefix string) {
	logger.Info().Msg("Setting up profiling.")

	profiling.StartProfiler("cpu", outFilePrefix+".cpu", 1)
	profiling.StartProfiler("block", outFilePrefix+".block", 1)
	profiling.StartProfiler("mutex", outFilePrefix+".mutex", 1)

	// Stop profiler on INT signal
	// TODO: Once graceful termination is implemented, use defer StopProfiler()
	profiling.StopOnSignal(os.Interrupt, true)
}

// Sets up tracing of events.
func setUpTracing(outFileName string, ownID int32) {

	// Initialize tracing with output file name given at command line
	tracing.MainTrace.Start(outFileName, ownID)

	// TODO: Move the CPU tracing to a more appropriate place
	//       For now, it is here, as it depends on tracing being enabled.
	profiling.StartCPUTracing(tracing.MainTrace, 500*time.Millisecond)

	// Stop tracing on INT signal.
	// TODO: Once graceful termination is implemented, use defer
	// The second parameter determines whether to shut down the process after stopping the tracing.
	// If profiling is on, the profiler will do the job.
	// TODO: ATTENTION! Implement some synchronization here, otherwise the profiler might exit the process before
	//                  the tracer is done flushing its buffers.
	tracing.MainTrace.StopOnSignal(os.Interrupt, !profilingEnabled)

	logger.Info().Str("traceFile", outFileName).Msg("Started tracing.")
}

func setManager(managerType string) (mngr manager.Manager) {
	switch managerType {
	case "Dummy":
		mngr = manager.NewDummyManager()
	case "Mir":
		mngr = manager.NewMirManager()
	default:
		logger.Fatal().Msg("Unsupported manager type")
	}
	return mngr
}

func setOrderer(ordererType string) (ord orderer.Orderer) {
	switch ordererType {
	case "Dummy":
		ord = &orderer.DummyOrderer{}
	case "Pbft":
		ord = &orderer.PbftOrderer{}
	case "HotStuff":
		ord = &orderer.HotStuffOrderer{}
	case "Raft":
		ord = &orderer.RaftOrderer{}
	default:
		logger.Fatal().Msg("Unsupported orderer type")
	}
	return ord
}

func setCheckpointer(managerType string) (chkp checkpoint.Checkpointer) {
	switch managerType {
	case "Simple":
		chkp = checkpoint.NewSimpleCheckpointer()
	case "Signing":
		chkp = checkpoint.NewSigningCheckpointer()
	default:
		logger.Fatal().Msg("Unsupported manager type")
	}
	return chkp
}

func Max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func Min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
