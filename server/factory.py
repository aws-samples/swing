import server


def stable_enough_notifier_server_creator(option,
                                          make_up_stable_enough_event_pipe_w,
                                          make_up_stable_enough_event_ack_pipe_r,
                                          make_down_stable_enough_event_pipe_w,
                                          make_down_stable_enough_event_ack_pipe_r):
    return server.StableEnoughNotifyServer("stable-enough-notifier-server",
                                           option,
                                           make_up_stable_enough_event_pipe_w,
                                           make_up_stable_enough_event_ack_pipe_r,
                                           make_down_stable_enough_event_pipe_w,
                                           make_down_stable_enough_event_ack_pipe_r)


def make_up_handler_server_creator(option, make_up_stable_enough_event_pipe_r, make_up_stable_enough_event_ack_pipe_w):
    return server.MakeUpServer("make-up-handler-server",
                               option,
                               make_up_stable_enough_event_pipe_r,
                               make_up_stable_enough_event_ack_pipe_w)


def make_down_handler_server_creator(option, make_down_stable_enough_event_pipe_r,
                                     make_down_stable_enough_event_ack_pipe_w):
    return server.MakeDownServer("make-down-handler-server",
                                 option,
                                 make_down_stable_enough_event_pipe_r,
                                 make_down_stable_enough_event_ack_pipe_w)
