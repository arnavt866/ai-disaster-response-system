import { apiRequest } from "./client";

export const getFieldTeams = () => apiRequest("/field-teams/");
export const createFieldTeam = (payload) =>
  apiRequest("/field-teams/", { method: "POST", body: JSON.stringify(payload) });
export const updateFieldTeamStatus = (teamId, status) =>
  apiRequest(`/field-teams/${teamId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
