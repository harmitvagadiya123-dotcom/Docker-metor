"""
LinkedIn API integration tool.
Posts content directly to LinkedIn using the REST API.
Replaces the Make.com LinkedIn CreatePost module.
"""

import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# LinkedIn API endpoints
LINKEDIN_API_BASE = "https://api.linkedin.com"
LINKEDIN_POSTS_URL = f"{LINKEDIN_API_BASE}/rest/posts"
LINKEDIN_USERINFO_URL = f"{LINKEDIN_API_BASE}/v2/userinfo"


class LinkedInService:
    """
    Handles posting content to LinkedIn via the REST API.
    Replaces Make.com's linkedin:CreatePost module.
    
    Posts are created with:
    - visibility: PUBLIC
    - distribution: MAIN_FEED
    - reshare: enabled
    """

    def __init__(self, access_token: str, person_urn: str):
        """
        Initialize LinkedIn service.
        
        Args:
            access_token: OAuth2 access token with w_member_social scope
            person_urn: LinkedIn person URN (e.g., urn:li:person:abc123)
        """
        self.access_token = access_token
        self.person_urn = person_urn

        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "202604",
        }

        logger.info(f"[-] LinkedIn service initialized for: {person_urn}")

    def verify_token(self) -> bool:
        """
        Verify that the access token is valid.
        
        Returns:
            True if token is valid
        """
        try:
            response = requests.get(
                LINKEDIN_USERINFO_URL,
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                name = data.get("name", "Unknown")
                logger.info(f"[OK] LinkedIn token valid - Authenticated as: {name}")
                return True
            else:
                logger.error(
                    f"[FAIL] LinkedIn token invalid - Status: {response.status_code}, "
                    f"Response: {response.text[:200]}"
                )
                return False
        except Exception as e:
            logger.error(f"[ERROR] Error verifying LinkedIn token: {e}")
            return False

    def create_post(
        self,
        content: str,
        visibility: str = "PUBLIC",
        feed_distribution: str = "MAIN_FEED",
    ) -> dict:
        """
        Create a LinkedIn post.
        Replicates Make.com's linkedin:CreatePost with:
        - visibility: PUBLIC
        - feedDistribution: MAIN_FEED
        - isReshareDisabledByAuthor: false
        
        Args:
            content: The post text content
            visibility: Post visibility (PUBLIC, CONNECTIONS, LOGGED_IN)
            feed_distribution: Feed distribution type (MAIN_FEED, NONE)
            
        Returns:
            Dict with post creation result
        """
        logger.info("[^] Posting to LinkedIn...")
        logger.info(f"  Content length: {len(content)} chars")
        logger.info(f"  Visibility: {visibility}")
        logger.info(f"  Distribution: {feed_distribution}")

        payload = {
            "author": self.person_urn,
            "commentary": content,
            "visibility": visibility,
            "distribution": {
                "feedDistribution": feed_distribution,
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }

        try:
            response = requests.post(
                LINKEDIN_POSTS_URL,
                headers=self.headers,
                json=payload,
                timeout=30,
            )

            if response.status_code in (200, 201):
                # LinkedIn returns the post ID in the x-restli-id header
                post_id = response.headers.get("x-restli-id", "unknown")
                logger.info(f"[OK] LinkedIn post created successfully!")
                logger.info(f"  Post ID: {post_id}")
                return {
                    "success": True,
                    "post_id": post_id,
                    "status_code": response.status_code,
                }
            else:
                error_msg = response.text[:500]
                logger.error(
                    f"[FAIL] LinkedIn post failed - Status: {response.status_code}"
                )
                logger.error(f"  Response: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "status_code": response.status_code,
                }

        except requests.exceptions.Timeout:
            logger.error("[FAIL] LinkedIn API request timed out")
            return {"success": False, "error": "Request timed out"}
        except Exception as e:
            logger.error(f"[ERROR] Error posting to LinkedIn: {e}")
            return {"success": False, "error": str(e)}
