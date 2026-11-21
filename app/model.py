"""Small decoder-only transformer trained from random initialization."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import torch
from torch import nn


@dataclass(frozen=True)
class ModelConfig:
    vocab_size: int
    context_length: int = 256
    embedding_size: int = 128
    layers: int = 2
    heads: int = 4
    dropout: float = 0.1

    def validate(self) -> None:
        if self.vocab_size < 2:
            raise ValueError("Словарь должен содержать хотя бы два токена.")
        if self.embedding_size % self.heads != 0:
            raise ValueError("Размер модели должен делиться на число голов.")
        if self.context_length < 8:
            raise ValueError("Контекст должен быть не меньше 8 токенов.")

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)


class CausalSelfAttention(nn.Module):
    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        self.heads = config.heads
        self.head_size = config.embedding_size // config.heads
        self.qkv = nn.Linear(config.embedding_size, 3 * config.embedding_size)
        self.output = nn.Linear(config.embedding_size, config.embedding_size)
        self.dropout = nn.Dropout(config.dropout)
        mask = torch.triu(
            torch.ones(config.context_length, config.context_length, dtype=torch.bool),
            diagonal=1,
        )
        self.register_buffer("causal_mask", mask, persistent=False)

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        batch, length, channels = values.shape
        qkv = self.qkv(values).view(batch, length, 3, self.heads, self.head_size)
        query, key, value = qkv.permute(2, 0, 3, 1, 4).unbind(0)
        scores = (query @ key.transpose(-2, -1)) / math.sqrt(self.head_size)
        scores = scores.masked_fill(self.causal_mask[:length, :length], -1.0e4)
        weights = self.dropout(torch.softmax(scores, dim=-1))
        attended = weights @ value
        attended = attended.transpose(1, 2).contiguous().view(batch, length, channels)
        return self.output(attended)


class FeedForward(nn.Module):
    def __init__(self, embedding_size: int, dropout: float) -> None:
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(embedding_size, 4 * embedding_size),
            nn.GELU(),
            nn.Linear(4 * embedding_size, embedding_size),
            nn.Dropout(dropout),
        )

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        return self.layers(values)


class TransformerBlock(nn.Module):
    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        self.norm_attention = nn.LayerNorm(config.embedding_size)
        self.attention = CausalSelfAttention(config)
        self.norm_feedforward = nn.LayerNorm(config.embedding_size)
        self.feedforward = FeedForward(config.embedding_size, config.dropout)

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        values = values + self.attention(self.norm_attention(values))
        values = values + self.feedforward(self.norm_feedforward(values))
        return values


class TinyLanguageModel(nn.Module):
    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        config.validate()
        self.config = config
        self.token_embedding = nn.Embedding(config.vocab_size, config.embedding_size)
        self.position_embedding = nn.Embedding(config.context_length, config.embedding_size)
        self.dropout = nn.Dropout(config.dropout)
        self.blocks = nn.ModuleList(TransformerBlock(config) for _ in range(config.layers))
        self.final_norm = nn.LayerNorm(config.embedding_size)
        self.language_head = nn.Linear(config.embedding_size, config.vocab_size, bias=False)
        self.language_head.weight = self.token_embedding.weight
        self.apply(self._initialize_weights)

    @staticmethod
    def _initialize_weights(module: nn.Module) -> None:
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(self, token_ids: torch.Tensor) -> torch.Tensor:
        _, length = token_ids.shape
        if length > self.config.context_length:
            raise ValueError("Вход длиннее максимального контекста модели.")
        positions = torch.arange(length, device=token_ids.device)
        values = self.token_embedding(token_ids) + self.position_embedding(positions)
        values = self.dropout(values)
        for block in self.blocks:
            values = block(values)
        return self.language_head(self.final_norm(values))

    @torch.no_grad()
    def generate(
        self,
        token_ids: torch.Tensor,
        max_new_tokens: int,
        temperature: float = 0.9,
        top_k: int = 40,
        end_token_id: int | None = None,
    ) -> torch.Tensor:
        self.eval()
        for _ in range(max_new_tokens):
            context = token_ids[:, -self.config.context_length :]
            logits = self(context)[:, -1, :]
            logits = logits / max(float(temperature), 1e-4)
            if 0 < top_k < logits.shape[-1]:
                cutoff = torch.topk(logits, top_k, dim=-1).values[:, -1:]
                logits = logits.masked_fill(logits < cutoff, float("-inf"))
            probabilities = torch.softmax(logits, dim=-1)
            next_token = torch.multinomial(probabilities, num_samples=1)
            token_ids = torch.cat((token_ids, next_token), dim=1)
            if end_token_id is not None and int(next_token.item()) == end_token_id:
                break
        return token_ids


def preset_values(preset: str) -> tuple[int, int, int]:
    """Return embedding size, layer count and attention-head count."""
    presets = {
        "Маленькая": (128, 2, 4),
        "Сбалансированная": (192, 4, 4),
        "Покрупнее": (256, 6, 8),
        "Большая": (384, 8, 8),
        "Очень большая": (512, 10, 8),
        "Максимальная": (768, 12, 12),
    }
    return presets.get(preset, presets["Маленькая"])
