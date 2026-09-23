"""Meter provider operations without holding a permit during child execution."""

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import ConfigDict

from harness.contracts import Rejected
from harness.runtime import Ledger


class MeteredModel(BaseChatModel):
    """Async model wrapper; counts attempted inference, including summarization."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    inner: Any  # bind_tools may produce a framework Runnable rather than a chat model.
    account: Ledger

    @property
    def _llm_type(self):
        return "harness-metered"

    @property
    def profile(self):
        return getattr(self.inner, "profile", {})

    def bind_tools(self, tools, **kwargs):
        return type(self)(inner=self.inner.bind_tools(tools, **kwargs), account=self.account)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        raise Rejected("Synchronous inference is disabled; use ainvoke")

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        config = {"callbacks": run_manager.handlers} if run_manager else {}
        response = await self.account.model_call(
            lambda: self.inner.ainvoke(messages, config=config, stop=stop, **kwargs)
        )
        return ChatResult(generations=[ChatGeneration(message=response)])


def metered_model(base_model: BaseChatModel, ledger: Ledger) -> MeteredModel:
    return MeteredModel(inner=base_model, account=ledger)
