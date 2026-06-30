"""AI-powered match verification using Agent Router API.

This package contains all verification-related modules for drug matching:
- verifier: Main AIVerifier class interface
- verifier_core: Core helper functions and constants
- verifier_core_extract: JSON parsing and extraction
- verifier_core_format: Candidate formatting and component context
- verifier_helpers: Helper functions (deprecated, use verifier_core)
- verifier_methods: AIVerifier method implementations
- verifier_request: Request building and API call execution
- verifier_request_build: Request planning and rotation management
- verifier_request_parse: Response parsing and handling
- verifier_request_validate: Failure tracking and validation
- verifier_response: Response processing and conflict resolution
- verifier_review: Second-opinion verification
- verifier_search: AI-powered candidate selection
"""
