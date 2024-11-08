from beer_garden.api.http.handlers import AuthorizationHandler
from beer_garden.errors import EndpointRemovedException


class CommandPublishingBlocklistPathAPI(AuthorizationHandler):
    def delete(self, command_publishing_id):
        """
        ---
        summary: Remove a command from event publishing block list
        deprecated: true
        parameters:
          - name: command_publishing_id
            in: path
            required: true
            description: id of entry in command publishing block list
            type: string
        responses:
          204:
            description: Command has been successfully removed from block list
            content:
              application/json:
                schema:
                  $ref: '#/components/schemas/CommandPublishingBlocklist'
          404:
            description: Resource does not exist
            content:
              text/plain:
                schema: 
                  type: 'string'
                example: Resource does not exist
          50x:
            description: Server exception
            content:
              text/plain:
                schema: 
                  type: 'string'
                example: Server exception
        tags:
          - Deprecated
        """
        raise EndpointRemovedException(
            message=("Command publishing blocklist API has been removed.")
        )


class CommandPublishingBlocklistAPI(AuthorizationHandler):
    def get(self):
        """
        ---
        summary: Retrieve list of commands in publishing block list
        deprecated: true
        responses:
          200:
            description: list of commands in publishing block list
            content:
              application/json:
                schema:
                  $ref: '#/components/schemas/CommandPublishingBlocklistListSchema'
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
          - Deprecated
        """
        raise EndpointRemovedException(
            message=("Command publishing blocklist API has been removed.")
        )

    def post(self):
        """
        ---
        summary: Add a list of commands to event publishing block list
        deprecated: true
        requestBody:
          name: CommandPublishingBlocklist
          description: The system, namespace and command name
          content:
              application/json:
                schema:
                  $ref: '#/components/schemas/CommandPublishingBlocklistListInputSchema'
        consumes:
          - application/json
        responses:
          201:
            description: list of commands that have been added to publishing block list
            content:
              application/json:
                schema:
                  $ref: '#/components/schemas/CommandPublishingBlocklistListSchema'
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
          - Deprecated
        """
        raise EndpointRemovedException(
            message=("Command publishing blocklist API has been removed.")
        )
