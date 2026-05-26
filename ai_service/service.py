"""
ai_service/service.py

MockAIService — deterministic, rule-based AI simulation.

Design goals:
  - Zero external dependencies (no API calls, no randomness)
  - Same input always produces the same output (deterministic)
  - Clean class interface so a real LLM can replace it later
    by only changing this file — zero changes to visit views.

Swap-in point:
  Replace MockAIService.generate_output() with a real provider call:
    - OpenAI: openai.chat.completions.create(...)
    - Gemini: genai.GenerativeModel(...).generate_content(...)
    - Anthropic: anthropic.messages.create(...)
"""


class MockAIService:
    """
    Simulates AI analysis of visit notes.

    Usage:
        service = MockAIService()
        result = service.generate_output(notes="Customer refused entry.", visit=visit_obj)
        # result = {
        #     'summary': '...',
        #     'follow_up': '...',
        #     'risk_flag': 'high'
        # }
    """

    # ── Risk keyword lists ────────────────────────────────────
    # Words that push the risk level up. Checked in order (high first).
    RISK_KEYWORDS = {
        'high': [
            'refused', 'hostile', 'aggressive', 'emergency', 'critical',
            'urgent', 'escalate', 'damage', 'damaged', 'broken', 'absent',
            'missing', 'theft', 'stolen', 'fire', 'flood', 'accident',
            'injury', 'unsafe', 'hazard', 'unresponsive', 'closed down',
            'not found', 'locked', 'denied',
        ],
        'medium': [
            'delayed', 'delay', 'partial', 'complaint', 'complain',
            'issue', 'problem', 'concern', 'rescheduled', 'pending',
            'incomplete', 'unable', 'difficult', 'challenging', 'busy',
            'unavailable', 'not available', 'waiting', 'follow up',
        ],
    }

    # ── Follow-up recommendation by risk level ────────────────
    FOLLOW_UP_MAP = {
        'high': (
            'URGENT: Escalate to Team Lead immediately. '
            'Schedule a priority re-visit within 24 hours. '
            'Document all findings and notify Regional Manager.'
        ),
        'medium': (
            'Flag for review. Schedule a follow-up visit within 3 business days. '
            'Notify Team Lead of the pending concern.'
        ),
        'low': (
            'No immediate action required. '
            'Archive visit record and proceed with regular schedule.'
        ),
    }

    # ── Summary templates by outcome ─────────────────────────
    SUMMARY_TEMPLATES = {
        'successful': (
            'Visit completed successfully by {agent} at {location}. '
            'Agent notes: "{preview}". '
            'All objectives were met with no major issues reported.'
        ),
        'failed': (
            'Visit by {agent} at {location} was unsuccessful. '
            'Agent notes: "{preview}". '
            'Objectives could not be completed. Immediate follow-up required.'
        ),
        'partial': (
            'Visit by {agent} at {location} was partially completed. '
            'Agent notes: "{preview}". '
            'Some objectives remain open and require a follow-up visit.'
        ),
        'pending': (
            'Visit recorded by {agent} at {location}. '
            'Agent notes: "{preview}". '
            'Outcome is still being assessed.'
        ),
    }

    # ─────────────────────────────────────────────────────────
    # Public interface
    # ─────────────────────────────────────────────────────────

    def generate_output(self, notes: str, visit) -> dict:
        """
        Main entry point. Accepts visit notes and a Visit object.
        Returns a dict with summary, follow_up, and risk_flag.

        This is the method to replace when integrating a real LLM.
        """
        if not notes or not notes.strip():
            return self._empty_output()

        risk_flag = self._detect_risk(notes)
        summary = self._generate_summary(notes, visit)
        follow_up = self.FOLLOW_UP_MAP[risk_flag]

        return {
            'summary': summary,
            'follow_up': follow_up,
            'risk_flag': risk_flag,
        }

    # ─────────────────────────────────────────────────────────
    # Private helpers
    # ─────────────────────────────────────────────────────────

    def _detect_risk(self, notes: str) -> str:
        """
        Scan notes (case-insensitive) against keyword lists.
        High keywords take priority over medium.
        Returns: 'high', 'medium', or 'low'
        """
        text = notes.lower()

        for keyword in self.RISK_KEYWORDS['high']:
            if keyword in text:
                return 'high'

        for keyword in self.RISK_KEYWORDS['medium']:
            if keyword in text:
                return 'medium'

        return 'low'

    def _generate_summary(self, notes: str, visit) -> str:
        """
        Fill a template with visit context.
        Truncates notes to first 30 words as the preview.
        """
        words = notes.split()
        preview = ' '.join(words[:30])
        if len(words) > 30:
            preview += '...'

        # Get agent name safely
        try:
            agent_name = visit.agent.get_full_name() or visit.agent.username
        except Exception:
            agent_name = 'Field Agent'

        location = getattr(visit, 'location', 'the site') or 'the site'
        outcome = getattr(visit, 'outcome', 'pending') or 'pending'

        template = self.SUMMARY_TEMPLATES.get(outcome, self.SUMMARY_TEMPLATES['pending'])

        return template.format(
            agent=agent_name,
            location=location,
            preview=preview,
        )

    def _empty_output(self) -> dict:
        """Returned when notes are blank."""
        return {
            'summary': 'No notes were provided for this visit.',
            'follow_up': self.FOLLOW_UP_MAP['low'],
            'risk_flag': 'low',
        }
