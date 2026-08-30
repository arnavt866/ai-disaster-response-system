import { apiRequest } from "./client";

export const getMissions = () => apiRequest("/missions/");
export const createMission = (payload) =>
  apiRequest("/missions/", { method: "POST", body: JSON.stringify(payload) });
export const updateMissionStatus = (missionId, status) =>
  apiRequest(`/missions/${missionId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
export const assignMissionTeam = (missionId, fieldTeamId) =>
  apiRequest(`/missions/${missionId}/team`, {
    method: "PATCH",
    body: JSON.stringify({ field_team_id: fieldTeamId }),
  });
