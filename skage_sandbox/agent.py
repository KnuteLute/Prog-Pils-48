from lux.utils import direction_to
import sys
import numpy as np

def create_relic_cluster(center) -> np.ndarray:
    cluster = np.array([np.array([w , h]) for w in range(center[0]-2,center[0]+3) for h in range(center[1]-2,center[1]+3)])
    return cluster

def calculate_distance(pos1, pos2):
    return np.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)


class Agent():
    def __init__(self, player: str, env_cfg) -> None:
        self.player = player
        self.opp_player = "player_1" if self.player == "player_0" else "player_0"
        self.team_id = 0 if self.player == "player_0" else 1
        self.opp_team_id = 1 if self.team_id == 0 else 0
        np.random.seed(0)
        self.env_cfg = env_cfg
        
        self.relic_node_positions = []
        self.discovered_relic_nodes_ids = set()
        self.unit_explore_locations = dict()
        self.enemy_discovered_relic_id = []
        self.enemy_discovered_relic_positions = []

    def act(self, step: int, obs, remainingOverageTime: int = 60):
        """implement this function to decide what actions to send to each available unit. 
        
        step is the current timestep number of the game starting from 0 going up to max_steps_in_match * match_count_per_episode - 1.
        """
        unit_mask = np.array(obs["units_mask"][self.team_id]) # shape (max_units, )
        unit_positions = np.array(obs["units"]["position"][self.team_id]) # shape (max_units, 2)
        unit_energys = np.array(obs["units"]["energy"][self.team_id]) # shape (max_units, 1)
        observed_relic_node_positions = np.array(obs["relic_nodes"]) # shape (max_relic_nodes, 2)
        observed_relic_nodes_mask = np.array(obs["relic_nodes_mask"]) # shape (max_relic_nodes, )
        team_points = np.array(obs["team_points"]) # points of each team, team_points[self.team_id] is the points of the your team
        
        # ids of units you can control at this timestep
        available_unit_ids = np.where(unit_mask)[0]
        # visible relic nodes
        visible_relic_node_ids = set(np.where(observed_relic_nodes_mask)[0])
        
        actions = np.zeros((self.env_cfg["max_units"], 3), dtype=int)

        undiscovered_relic_clusters = []


        # basic strategy here is simply to have some units randomly explore and some units collecting as much energy as possible
        # and once a relic node is found, we send all units to move randomly around the first relic node to gain points
        # and information about where relic nodes are found are saved for the next match
        
        # save any new relic nodes that we discover for the rest of the game.

        # We find new clusters 
        
        for id in visible_relic_node_ids:
            if id not in self.discovered_relic_nodes_ids:
                self.discovered_relic_nodes_ids.add(id)
                self.relic_node_positions.append(observed_relic_node_positions[id])
                undiscovered_relic_clusters.append((id, create_relic_cluster( observed_relic_node_positions[id])))

        
        u_enemy = obs['units']['position'][self.opp_team_id]
        seen_enemy_units = [enemy for enemy in u_enemy if not np.array_equal(enemy, np.array([-1, -1]))]

        # Check if relic nodes are discovered by the enemy
        if len(undiscovered_relic_clusters) > 0:
            for idx, cluster in enumerate(undiscovered_relic_clusters):
                for enemy in seen_enemy_units:
                    if enemy in cluster[1]:
                        undiscovered_relic_clusters.pop(idx)
                        self.enemy_discovered_relic_id.append(cluster[0])
                        self.enemy_discovered_relic_positions.append(observed_relic_node_positions[cluster[0]])
                        

        # unit ids range from 0 to max_units - 1
        for idx, unit_id in enumerate(available_unit_ids):
            unit_pos = unit_positions[unit_id]
            unit_energy = unit_energys[unit_id]

            

        for idx, unit_id in enumerate(available_unit_ids):
            unit_pos = unit_positions[unit_id]
            unit_energy = unit_energys[unit_id]

            scout_locations = [(0, 0), (0, self.env_cfg["map_height"] - 1), (self.env_cfg["map_width"] - 1, 0), (self.env_cfg["map_width"] - 1, self.env_cfg["map_height"] - 1)]
            if unit_id < 4:
                actions[unit_id] = [direction_to(unit_pos, scout_locations[unit_id]), 0, 0]
            else:
                if unit_id % 2 == 0:
                    # Basic bot behaviour on half of the units
                    if len(self.relic_node_positions) > 0:
                        nearest_relic_node_position = self.relic_node_positions[0]
                        manhattan_distance = abs(unit_pos[0] - nearest_relic_node_position[0]) + abs(unit_pos[1] - nearest_relic_node_position[1])
                        
                        # if close to the relic node we want to hover around it and hope to gain points
                        if manhattan_distance <= 4:
                            random_direction = np.random.randint(0, 5)
                            actions[unit_id] = [random_direction, 0, 0]
                        else:
                            # otherwise we want to move towards the relic node
                            actions[unit_id] = [direction_to(unit_pos, nearest_relic_node_position), 0, 0]
                    else:
                        # randomly explore by picking a random location on the map and moving there for about 20 steps
                        if step % 20 == 0 or unit_id not in self.unit_explore_locations:
                            rand_loc = (np.random.randint(0, self.env_cfg["map_width"]), np.random.randint(0, self.env_cfg["map_height"]))

                            self.unit_explore_locations[unit_id] = rand_loc
                        actions[unit_id] = [direction_to(unit_pos, self.unit_explore_locations[unit_id]), 0, 0]
                else:
                    # Attack strategy on half of the units
                    if len(self.enemy_discovered_relic_positions) > 0:
                        nearest_idx = np.argmin([calculate_distance(unit_pos, relic_pos) for relic_pos in self.enemy_discovered_relic_positions])
                        nearest_enemy_relic_pos = self.enemy_discovered_relic_positions[nearest_idx]

                        manhattan_distance = abs(unit_pos[0] - nearest_enemy_relic_pos[0]) + abs(unit_pos[1] - nearest_enemy_relic_pos[1])
                        
                        # if close to the relic node we want to hover around it and hope to gain points
                        actions[unit_id] = [direction_to(unit_pos, nearest_enemy_relic_pos), 0, 0]
                        if manhattan_distance < 3:
                            for unit in seen_enemy_units:
                                if np.array_equal(unit, nearest_enemy_relic_pos):
                                    actions[unit_id] = [5, unit[0]-nearest_enemy_relic_pos[0], unit[1]-nearest_enemy_relic_pos[1]]     
                            
                            
                            

                        

                











        if step % 90 == 0:
            from json_tricks import dump
            debug_lob = {
                'self.enemy_discovered_relic_positions': self.enemy_discovered_relic_positions,
                'seen_enemy_units': seen_enemy_units,
                'obs': obs,
                'unit_mask': unit_mask.astype(int).tolist(),
                'unit_positions': unit_positions.astype(int).tolist(),
                'unit_energys': unit_energys.astype(int).tolist(),
                'observed_relic_node_positions': observed_relic_node_positions.astype(int).tolist(),
                'observed_relic_nodes_mask': observed_relic_nodes_mask.astype(int).tolist(),
                'available_unit_ids': available_unit_ids.astype(int).tolist(),
                'visible_relic_node_ids': [int(x) for x in visible_relic_node_ids]  # Convert set of NumPy ints to Python ints
            }
            
            with open('debug_lob.json', 'w') as f:
                dump(debug_lob, f, indent=4)

        return actions

if __name__ == '__main__':
    print(create_relic_cluster((3, 3)))
