"""Phase 2 simulation stub: dungeon + player exploration only."""

from __future__ import annotations

from dataclasses import dataclass

from gauntletsim.config import AppConfig
from gauntletsim.dungeon import DungeonState
from gauntletsim.game_rules import GameRules
from gauntletsim.room import Coord
from gauntletsim.visualization import render_ascii


@dataclass
class Phase2Sim:
    rules: GameRules
    config: AppConfig
    dungeon: DungeonState

    @classmethod
    def create(cls, rules: GameRules, config: AppConfig) -> Phase2Sim:
        dungeon = DungeonState.generate(rules, config.sim.master_seed)
        return cls(rules=rules, config=config, dungeon=dungeon)

    def ascii_map(self) -> str:
        return render_ascii(self.dungeon)

    def explore_to(self, goal: Coord, max_steps: int = 64) -> int:
        """Greedy explore toward goal by lighting fog when needed."""
        steps = 0
        while self.dungeon.player.coord != goal and steps < max_steps:
            self.dungeon.step_toward(goal)
            steps += 1
        return steps

    def status_lines(self) -> list[str]:
        d = self.dungeon
        return [
            "GauntletSim — Phase 2 dungeon",
            f"master_seed: {d.layout.master_seed}",
            f"start: ({d.layout.start.x},{d.layout.start.y})",
            f"boss: ({d.layout.boss.x},{d.layout.boss.y})",
            f"fish_room: ({d.layout.fish_room.x},{d.layout.fish_room.y}) "
            f"spots={d.room(d.layout.fish_room).fishing_spots}",
            f"demi_rooms: {len(d.layout.demi_rooms)}",
            f"layout_errors: {d.rules_errors if d.rules_errors else 'none'}",
            f"player_tick: {d.player.tick}",
        ]
