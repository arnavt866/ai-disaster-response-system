import { apiRequest } from "./client";

export const getFieldTeams = () => apiRequest("/field-teams/");
export const getFieldTeamById = (teamId) => apiRequest(`/field-teams/${teamId}`);
export const createFieldTeam = (payload) =>
  apiRequest("/field-teams/", { method: "POST", body: JSON.stringify(payload) });
export const updateFieldTeam = (teamId, payload) =>
  apiRequest(`/field-teams/${teamId}`, { method: "PUT", body: JSON.stringify(payload) });
export const deactivateFieldTeam = (teamId) =>
  apiRequest(`/field-teams/${teamId}`, { method: "DELETE" });
export const updateFieldTeamStatus = (teamId, status) =>
  apiRequest(`/field-teams/${teamId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
