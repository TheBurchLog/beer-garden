from brewtils.models import Permissions
from brewtils.schema_parser import SchemaParser

from beer_garden.api.http.handlers import AuthorizationHandler
from beer_garden.events import publish
from beer_garden.metrics import collect_metrics


class EventPublisherAPI(AuthorizationHandler):
    parser = SchemaParser()

    @collect_metrics(transaction_type="API", group="EventPublisherAPI")
    def post(self):
        """
        ---
        summary: Publish a new event
        requestBody:
          name: event
          description: The the Event object
          content:
              application/json:
                schema: 'Event'
        parameters:
          - name: bg-namespace
            in: header
            required: false
            description: Namespace to use
            type: string
        responses:
          204:
            description: An Event has been published
          400:
            description: Parameter validation error
            content:
              text/plain:
                schema: 
                  type: 'string'
                example: Parameter validation error
          50x:
            description: Server exception
            content:
              text/plain:
                schema: 
                  type: 'string'
                example: Server exception
        tags:
          - Event
        """
        self.minimum_permission = Permissions.OPERATOR.name
        event = SchemaParser.parse_event(self.request.decoded_body, from_string=True)
        self.verify_user_permission_for_object(event)
        publish(event)

        self.set_status(204)
