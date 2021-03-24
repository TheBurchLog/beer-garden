import stomp
import logging
from brewtils.schema_parser import SchemaParser
import beer_garden.events
import beer_garden.router
from beer_garden.api.stomp.processors import append_headers, process_send_message

logger = logging.getLogger(__name__)


def send_message(
    message=None,
    garden_headers: dict = None,
    conn: stomp.Connection = None,
    send_destination: str = None,
    request_headers: dict = None,
):
    message, response_headers = process_send_message(message)

    response_headers = append_headers(
        response_headers=response_headers,
        request_headers=request_headers,
        garden_headers=garden_headers,
    )

    if conn.is_connected() and send_destination:
        if "reply-to" in (request_headers or {}):
            conn.send(
                body=message,
                headers=response_headers,
                destination=request_headers["reply-to"],
            )
        else:
            conn.send(
                body=message,
                headers=response_headers,
                destination=send_destination,
            )


def send_error_msg(
    error_msg=None,
    request_headers=None,
    conn=None,
    send_destination=None,
    garden_headers=None,
):
    error_headers = {"model_class": "error_message"}

    error_headers = append_headers(
        response_headers=error_headers,
        request_headers=request_headers or {},
        garden_headers=garden_headers or {},
    )

    if conn.is_connected():
        if "reply-to" in request_headers:
            conn.send(
                body=error_msg,
                headers=error_headers,
                destination=request_headers["reply-to"],
            )
        elif send_destination:
            conn.send(
                body=error_msg,
                headers=error_headers,
                destination=send_destination,
            )


class OperationListener(stomp.ConnectionListener):
    def __init__(self, conn=None, send_destination=None):
        self.conn = conn
        self.send_destination = send_destination

    def on_error(self, headers, message):
        logger.warning("received an error:" + str(headers))

    def on_message(self, headers, message):
        try:
            operation = SchemaParser.parse_operation(message, from_string=True)
            if hasattr(operation, "kwargs"):
                operation.kwargs.pop("wait_timeout", None)
            result = beer_garden.router.route(operation)
            if result:
                send_message(
                    message=result,
                    request_headers=headers,
                    conn=self.conn,
                    send_destination=self.send_destination,
                )
        except Exception as e:
            send_error_msg(
                error_msg=str(e),
                request_headers=headers,
                conn=self.conn,
                send_destination=self.send_destination,
            )
            logger.warning(str(e))


class Connection:
    """Stomp connection wrapper

    Args:
        host_and_ports:
        send_destination:
        subscribe_destination:
        ssl:
        username:
        password:

    """

    def __init__(
        self,
        host_and_ports=None,
        send_destination=None,
        subscribe_destination=None,
        ssl=None,
        username=None,
        password=None,
    ):
        self.host_and_ports = host_and_ports
        self.username = username
        self.password = password
        self.subscribe_destination = subscribe_destination
        self.send_destination = send_destination
        self.bg_active = True
        self.conn = stomp.Connection(
            host_and_ports=host_and_ports, heartbeats=(10000, 0)
        )
        if ssl:
            if ssl.get("use_ssl"):
                self.conn.set_ssl(
                    for_hosts=host_and_ports,
                    key_file=ssl.get("private_key"),
                    cert_file=ssl.get("cert_file"),
                )
        if subscribe_destination:
            self.conn.set_listener("", OperationListener(self.conn, send_destination))

    def connect(self, connected_message=None, wait_time=None, gardens=None):
        if self.host_and_ports:
            if (
                self.host_and_ports[0][0]
                and self.host_and_ports[0][1]
                and self.subscribe_destination
            ):
                try:
                    self.conn.connect(
                        username=self.username,
                        passcode=self.password,
                        wait=True,
                        headers={"client-id": self.username},
                    )
                    if self.subscribe_destination:
                        self.conn.subscribe(
                            destination=self.subscribe_destination,
                            id=self.username,
                            ack="auto",
                            headers={
                                "subscription-type": "MULTICAST",
                                "durable-subscription-name": self.subscribe_destination,
                            },
                        )
                    if connected_message is not None and self.conn.is_connected():
                        logger.info("Stomp successfully " + connected_message)

                except Exception as e:
                    logger.debug(
                        f"Error connecting: {type(e).__name__}. "
                        f"Affected gardens are {[garden.get('name') for garden in gardens]}"
                    )
                    logger.warning(
                        "Waiting %.1f seconds before next attempt", wait_time
                    )

    def disconnect(self):
        self.bg_active = False
        if self.conn.is_connected():
            self.conn.disconnect()

    def is_connected(self) -> bool:
        return self.conn.is_connected()

    def send_event(self, event=None, headers=None):
        send_message(
            message=event,
            conn=self.conn,
            send_destination=self.send_destination,
            garden_headers=headers,
        )
