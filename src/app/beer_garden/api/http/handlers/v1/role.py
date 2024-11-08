# -*- coding: utf-8 -*-
from brewtils.models import Operation, Permissions
from brewtils.schema_parser import SchemaParser

from beer_garden.api.http.handlers import AuthorizationHandler
from beer_garden.garden import local_garden
from beer_garden.metrics import collect_metrics


class RoleAPI(AuthorizationHandler):
    parser = SchemaParser()

    @collect_metrics(transaction_type="API", group="RoleAPI")
    async def get(self, role_id):
        """
        ---
        summary: Retrieve a specific Request
        parameters:
          - name: role_id
            in: path
            required: true
            description: The role id name of the Role
            type: string
        responses:
          200:
            description: Role with the given role name
            content:
              application/json:
                schema:
                  $ref: '#/components/schemas/Role'
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
          - Roles
        """
        self.minimum_permission = Permissions.GARDEN_ADMIN.name
        self.verify_user_global_permission()

        response = await self.process_operation(
            Operation(
                operation_type="ROLE_READ",
                kwargs={
                    "role_id": role_id,
                },
            ),
            filter_results=False,
        )

        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(response)

    @collect_metrics(transaction_type="API", group="RoleAPI")
    async def delete(self, role_id):
        """
        ---
        summary: Delete a specific Role
        parameters:
          - name: role_id
            in: path
            required: true
            description: The role id name of the Role
            type: string
        responses:
          204:
            description: Role has been successfully deleted
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
          - Roles
        """
        self.minimum_permission = Permissions.GARDEN_ADMIN.name
        self.verify_user_global_permission()
        await self.process_operation(
            Operation(
                operation_type="ROLE_DELETE",
                kwargs={
                    "role_id": role_id,
                },
            ),
            filter_results=False,
        )

        self.set_status(204)

    @collect_metrics(transaction_type="API", group="RoleAPI")
    async def patch(self, role_id):
        """
        ---
        summary: Partially update a Role
        requestBody:
          name: patch
          description: A subset of Role attributes to update
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Patch'
        parameters:
          - name: role_id
            in: path
            required: true
            description: The role id name of the Role
            type: string
        responses:
          200:
            description: Role with the given role name
            content:
              application/json:
                schema:
                  $ref: '#/components/schemas/Role'
          400:
            description: Parameter validation error
            content:
              text/plain:
                schema: 
                  type: 'string'
                example: Parameter validation error
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
          - Users
        """
        self.minimum_permission = Permissions.GARDEN_ADMIN.name
        self.verify_user_global_permission()

        patch = self.parser.parse_patch(self.request.decoded_body, from_string=True)

        for op in patch:
            operation = op.operation.lower()

            if operation == "update_role":
                response = await self.process_operation(
                    Operation(
                        operation_type="ROLE_UPDATE",
                        kwargs={
                            "role_id": role_id,
                            "role": self.parser.parse_role(op.value, from_string=False),
                        },
                    ),
                    filter_results=False,
                )

        self.write(response)


class RoleListAPI(AuthorizationHandler):
    parser = SchemaParser()

    @collect_metrics(transaction_type="API", group="RoleListAPI")
    async def get(self):
        """
        ---
        summary: Retrieve all Roles
        responses:
          200:
            description: All Roles
            content:
              application/json:
                schema:
                  $ref: '#/components/schemas/RoleList'
          50x:
            description: Server exception
            content:
              text/plain:
                schema: 
                  type: 'string'
                example: Server exception
        tags:
          - Roles
        """

        self.verify_user_permission_for_object(local_garden())

        response = await self.process_operation(
            Operation(operation_type="ROLE_READ_ALL")
        )

        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(response)

    @collect_metrics(transaction_type="API", group="RoleListAPI")
    async def post(self):
        """
        ---
        summary: Create a new Role
        requestBody:
          name: role
          description: The Role definition to create
          content:
              application/json:
                schema:
                  $ref: '#/components/schemas/Role'
        consumes:
          - application/json
        responses:
          201:
            description: A new Role has been created
            content:
              application/json:
                schema:
                  $ref: '#/components/schemas/Role'
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
          - Users
        """
        self.minimum_permission = Permissions.GARDEN_ADMIN.name
        self.verify_user_global_permission()

        role_model = self.parser.parse_role(self.request.decoded_body, from_string=True)

        response = await self.process_operation(
            Operation(operation_type="ROLE_CREATE", args=[role_model]),
            filter_results=False,
        )

        self.write(response)
        self.set_status(201)

    @collect_metrics(transaction_type="API", group="RoleListAPI")
    async def patch(self):
        """
        ---
        summary: Partially update a Role
        description: |
          The body of the request needs to contain a set of instructions detailing the
          updates to apply. Currently the only operations are:

          * rescan

          ```JSON
          [
            { "operation": "" }
          ]
          ```
        requestBody:
          name: patch
          description: Instructions for how to update the Role
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Patch'
        responses:
          204:
            description: Patch operation has been successfully forwarded
          400:
            description: Parameter validation error
            content:
              text/plain:
                schema: 
                  type: 'string'
                example: Parameter validation error
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
          - Users
        """
        self.minimum_permission = Permissions.GARDEN_ADMIN.name
        self.verify_user_global_permission()

        patch = self.parser.parse_patch(self.request.decoded_body, from_string=True)

        for op in patch:
            operation = op.operation.lower()
        if operation == "rescan":
            await self.process_operation(
                Operation(operation_type="ROLE_RESCAN"), filter_results=False
            )
        self.set_status(204)
