import logging
import re
from functools import lru_cache

import requests
from github import Github
from packageurl import PackageURL

from disclosurecheck.util.context import Context
from disclosurecheck.collectors.github import get_github_token

from ..util.searchers import sanitize_github_url

logger = logging.getLogger(__name__)


@lru_cache
def analyze_tidelift(purl: PackageURL, context: Context):
    """
    Checks to see if a package is covered by a Tidelift subscription.

    params:
        purl: PackageURL to check
    """
    if not purl:
        logger.warning("Missing PackageURL.")
        return

    if purl.namespace:
        # TODO: Validate this logic with Tidelift, unclear whether it's correct.
        suffix = purl.namespace.replace("@", ".") + "-" + purl.name
    else:
        suffix = purl.name

    logger.info("Searching for a Tidelift subscription.")
    url = f"https://tidelift.com/subscription/pkg/{purl.type}-{suffix}"
    logger.debug("Loading URL: [%s]", url)
    res = requests.get(url, timeout=30)

    if res.ok:
        context.contacts.append(
            {
                "priority": 5,
                "type": "tidelift",
                "name": "Tidelift Security",
                "value": "security@tidelift.com",
                "evidence": url,
            }
        )
    else:
        logger.warning("Error loading URL [%s]: %s", url, res.status_code)

    if purl.type == "github":
        logger.info("Searching for Tidelift references in the GitHub repository.")
        github_token = get_github_token()
        if not github_token:
            logger.warning("Unable to search GitHub for a Tidelift subscription without a GITHUB_TOKEN")
            return

        gh = Github(github_token)
        # Handle renames, since code search 422s out
        repo_obj = gh.get_repo(f"{purl.namespace}/{purl.name}")

        query = f"repo:{repo_obj.owner.login}/{repo_obj.name} security@tidelift.com"
        logger.debug("Searching for [%s]", query)
        files = gh.search_code(query)

        if files.totalCount:
            context.contacts.append(
                {
                    "priority": 5,
                    "type": "tidelift",
                    "value": "security@tidelift.com",
                    "evidence": ','.join([f.name for f in files]),
                }
            )
