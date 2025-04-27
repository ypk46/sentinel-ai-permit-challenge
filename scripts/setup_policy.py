import asyncio
import logging
import os

from dotenv import load_dotenv
from permit import Permit
from permit.exceptions import PermitAlreadyExistsError

load_dotenv()

PERMIT_API_KEY = os.getenv("PERMIT_API_KEY")
PERMT_PDP_URL = os.getenv("PERMIT_PDP_URL", "http://localhost:7766")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    # Initialize Permit
    permit = Permit(token=PERMIT_API_KEY, pdp=PERMT_PDP_URL)

    try:
        # Create resources
        await permit.api.resources.create(
            {
                "key": "document",
                "name": "Document",
                "actions": {
                    "read": {"description": "Read a document"},
                    "summarize": {"description": "Summarize a document"},
                },
                "attributes": {
                    "sensitivity": {
                        "type": "string",
                        "description": "Sensitivity level of the document",
                    },
                },
            }
        )
        logger.info("Resources created successfully.")
    except PermitAlreadyExistsError:
        logger.info("Resource 'document' already exists. Skipping creation.")

    # Create resource sets
    resourse_sets = [
        {
            "key": "low_sensitivity",
            "type": "resourceset",
            "resource_id": "document",
            "name": "Low sensitivity documents",
            "conditions": {"allOf": [{"resource.sensitivity": {"equals": "low"}}]},
        },
        {
            "key": "medium_sensitivity",
            "type": "resourceset",
            "resource_id": "document",
            "name": "Medium sensitivity documents",
            "conditions": {"allOf": [{"resource.sensitivity": {"equals": "medium"}}]},
        },
        {
            "key": "high_sensitivity",
            "type": "resourceset",
            "resource_id": "document",
            "name": "High sensitivity documents",
            "conditions": {"allOf": [{"resource.sensitivity": {"equals": "high"}}]},
        },
    ]

    for resource_set in resourse_sets:
        try:
            await permit.api.condition_sets.create(resource_set)
            logger.info(f"Resource set '{resource_set['key']}' created successfully.")
        except PermitAlreadyExistsError:
            logger.info(
                f"Resource set '{resource_set['key']}' already exists. Skipping creation."
            )

    # Create roles
    roles = [
        {
            "key": "manager",
            "name": "Manager",
            "description": "Manager role with full permissions",
            "permissions": [],
            "condition_set_rules": [
                {
                    "permission": "document:read",
                    "resource_set": "low_sensitivity",
                },
                {
                    "permission": "document:summarize",
                    "resource_set": "low_sensitivity",
                },
                {
                    "permission": "document:read",
                    "resource_set": "medium_sensitivity",
                },
                {
                    "permission": "document:summarize",
                    "resource_set": "medium_sensitivity",
                },
                {
                    "permission": "document:read",
                    "resource_set": "high_sensitivity",
                },
                {
                    "permission": "document:summarize",
                    "resource_set": "high_sensitivity",
                },
            ],
        },
        {
            "key": "employee",
            "name": "Employee",
            "description": "Employee role with medium-level access",
            "permissions": [],
            "condition_set_rules": [
                {
                    "permission": "document:read",
                    "resource_set": "low_sensitivity",
                },
                {
                    "permission": "document:read",
                    "resource_set": "medium_sensitivity",
                },
            ],
        },
        {
            "key": "user",
            "name": "User",
            "description": "User role with low-level access",
            "permissions": [],
            "condition_set_rules": [
                {
                    "permission": "document:read",
                    "resource_set": "low_sensitivity",
                },
            ],
        },
    ]

    for role_data in roles:
        # Pop the condition_set_rules from the role dictionary
        condition_set_rules = role_data.pop("condition_set_rules")

        try:
            await permit.api.roles.create(role_data)
            logger.info(f"Role '{role_data['key']}' created successfully.")
        except PermitAlreadyExistsError:
            logger.info(f"Role '{role_data['key']}' already exists. Skipping creation.")

        for rule in condition_set_rules:
            try:
                condition_set_rule_data = {"user_set": role_data["key"], **rule}
                await permit.api.condition_set_rules.create(condition_set_rule_data)
            except PermitAlreadyExistsError:
                pass

    # Create a user for each role
    users = [
        {
            "id": "manager_1",
            "name": "John",
            "last_name": "Doe",
            "roles": ["manager"],
        },
        {
            "id": "employee_1",
            "name": "Jane",
            "last_name": "Smith",
            "roles": ["employee"],
        },
        {
            "id": "user_1",
            "name": "Alice",
            "last_name": "Johnson",
            "roles": ["user"],
        },
    ]

    for user_data in users:
        try:
            await permit.api.users.create(
                {
                    "key": user_data["id"],
                    "email": f"{user_data['name'].lower()}@sentinel.ai",
                    "first_name": user_data["name"],
                    "last_name": user_data["last_name"],
                }
            )
            logger.info(f"User '{user_data['id']}' created successfully.")
        except PermitAlreadyExistsError:
            logger.info(f"User '{user_data['id']}' already exists. Skipping creation.")

        # Assign roles to the user
        for role in user_data["roles"]:
            try:
                await permit.api.role_assignments.assign(
                    {
                        "user": user_data["id"],
                        "role": role,
                        "tenant": "default",
                    }
                )
                logger.info(f"Role '{role}' assigned to user '{user_data['id']}'.")
            except PermitAlreadyExistsError:
                logger.info(
                    f"Role '{role}' already assigned to user '{user_data['id']}'. Skipping assignment."
                )


if __name__ == "__main__":
    asyncio.run(main())
