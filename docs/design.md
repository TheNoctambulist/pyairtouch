# Pyairtouch Design

This document describes some of the key design decisions made when implementing the `pyairtouch` library along with their rationale.

## TCP Connection Monitoring

### Context
Real world usage of the API has highlighted that, while some environments can happily maintain the open idle connection for long periods of time, there are situations where the idle connection will "crash" quite frequently.
Therefore, there is a need for `pyairtouch` to be robust against [half-open](https://en.wikipedia.org/wiki/TCP_half-open) connections.

In particular we want to ensure that when a client sends a command to the AirTouch it is reliably delivered.
Any dropped commands would force the client to implement complex retry logic.

When communicating via a TCP socket, the only way to reliably detect a half-open connection is to write data to the socket.
Neither the AirTouch 4 not AirTouch 5 interface specifications include any form of heartbeat mechanism.
The protocol also doesn't have any defined periodic messages which could be monitored for timeout.
However, there are several messages in the interface that can be sent at any time to request the latest status from the AirTouch.

### Design
In order to provide the desired command delivery guarantees and ensure that status updates are received even if no command is sent, a two-pronged approach is used:
1. Periodically send a request to the AirTouch as a heartbeat; and
2. Retry sending of commands for a short time if a re-connection is required when sending.

### Heartbeat
The Console Version Request (0xFF30) is used as the heartbeat for bot the AirTouch 4 and the AirTouch 5.
The Console Version Request has the advantage of being one of the smallest messages in the interface specifications, which results in low overhead.
Periodically requesting the Console Version also ensures timely notification when console updates are available.

The purpose of the heartbeat is primarily to keep the connection from being considered idle by any intermidiate devices on the network that may time out the connection (e.g. firewalls).
For this reason, the heartbeat interval can be fairly large.
A heartbeat interval of 300 seconds (5 minutes) has been selected based on the assumption that this will be less than typical firewall idle timeouts (which reading suggests typically default to 60 minutes).

The heartbeat response timeout is set to `heartbeat_interval + 30.0` seconds.
This allows the AirTouch up to 30 seconds to process the heartbeat and send a response.
Loss of a single heartbeat response is considered enough to trigger a connection reset.
Connection reset consits of closing the current TCP connection and attempting to re-establish a new connection.

### Retries
TODO: Document retries logic