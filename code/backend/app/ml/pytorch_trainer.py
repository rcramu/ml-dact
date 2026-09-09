"""PyTorch training pipeline (req.md Sec. 15-16) — a small feed-forward MLP
trained from scratch on the seeded synthetic customer-churn features."""
import numpy as np
import torch
from torch import nn


class ChurnMLP(nn.Module):
    def __init__(self, in_dim: int = 8, hidden1: int = 16, hidden2: int = 8):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden1), nn.ReLU(),
            nn.Linear(hidden1, hidden2), nn.ReLU(),
            nn.Linear(hidden2, 1),
        )

    def forward(self, x):
        return self.net(x).squeeze(-1)


def train_model(x_train: np.ndarray, y_train: np.ndarray, *, epochs: int, batch_size: int,
                 learning_rate: float, hidden1: int, hidden2: int, seed: int) -> tuple[ChurnMLP, float]:
    """Trains ChurnMLP with BCEWithLogitsLoss (class-balanced via pos_weight) + Adam. Returns (model, final_train_loss)."""
    torch.manual_seed(seed)
    model = ChurnMLP(x_train.shape[1], hidden1, hidden2)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

    n_pos = max(int(y_train.sum()), 1)
    n_neg = max(len(y_train) - n_pos, 1)
    pos_weight = torch.tensor(n_neg / n_pos, dtype=torch.float32)
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    x_t = torch.tensor(x_train, dtype=torch.float32)
    y_t = torch.tensor(y_train, dtype=torch.float32)
    n = x_t.shape[0]
    final_loss = 0.0

    model.train()
    for _epoch in range(epochs):
        perm = torch.randperm(n)
        epoch_loss = 0.0
        for start in range(0, n, batch_size):
            idx = perm[start:start + batch_size]
            optimizer.zero_grad()
            logits = model(x_t[idx])
            loss = loss_fn(logits, y_t[idx])
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item() * len(idx)
        final_loss = epoch_loss / max(n, 1)

    return model, final_loss


def predict(model: ChurnMLP, x: np.ndarray) -> np.ndarray:
    model.eval()
    with torch.no_grad():
        logits = model(torch.tensor(x, dtype=torch.float32))
        probs = torch.sigmoid(logits).numpy()
    return probs


def predict_labels(model: ChurnMLP, x: np.ndarray, threshold: float = 0.5) -> np.ndarray:
    return (predict(model, x) >= threshold).astype(int)


def best_threshold_for_f1(probs: np.ndarray, y_true: np.ndarray) -> float:
    """Standard practice: tune the decision threshold on a validation set to maximize F1,
    rather than assuming a naive 0.5 cutoff is well-calibrated for an imbalanced problem."""
    from sklearn.metrics import f1_score

    if len(set(y_true.tolist())) < 2:
        return 0.5
    best_t, best_f1 = 0.5, -1.0
    for t in np.linspace(0.05, 0.95, 37):
        f1 = f1_score(y_true, (probs >= t).astype(int), zero_division=0)
        if f1 > best_f1:
            best_f1, best_t = f1, t
    return float(best_t)
