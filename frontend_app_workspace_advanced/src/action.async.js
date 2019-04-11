import { FETCH_CONFIG } from './helper.js'

export const getWorkspaceDetail = (apiUrl, idWorkspace) =>
  fetch(`${apiUrl}/workspaces/${idWorkspace}`, {
    credentials: 'include',
    headers: {...FETCH_CONFIG.headers},
    method: 'GET'
  })

export const getWorkspaceMember = (apiUrl, idWorkspace) =>
  fetch(`${apiUrl}/workspaces/${idWorkspace}/members`, {
    credentials: 'include',
    headers: {...FETCH_CONFIG.headers},
    method: 'GET'
  })

export const putLabel = (apiUrl, workspace, newLabel) =>
  fetch(`${apiUrl}/workspaces/${workspace.workspace_id}`, {
    credentials: 'include',
    headers: {...FETCH_CONFIG.headers},
    method: 'PUT',
    body: JSON.stringify({
      label: newLabel,
      description: workspace.description,
      calendar_enabled: workspace.calendar_enabled
    })
  })

export const putDescription = (apiUrl, workspace, newDescription) =>
  fetch(`${apiUrl}/workspaces/${workspace.workspace_id}`, {
    credentials: 'include',
    headers: {...FETCH_CONFIG.headers},
    method: 'PUT',
    body: JSON.stringify({
      label: workspace.label,
      description: newDescription,
      calendar_enabled: workspace.calendar_enabled
    })
  })

export const putCalendarEnabled = (apiUrl, workspace, calendarEnabled) =>
  fetch(`${apiUrl}/workspaces/${workspace.workspace_id}`, {
    credentials: 'include',
    headers: {...FETCH_CONFIG.headers},method: 'PUT',
    body: JSON.stringify({
      label: workspace.label,
      description: workspace.description,
      calendar_enabled: calendarEnabled
    })
  })

export const putMemberRole = (apiUrl, idWorkspace, idMember, slugNewRole) =>
  fetch(`${apiUrl}/workspaces/${idWorkspace}/members/${idMember}`, {
    credentials: 'include',
    headers: {...FETCH_CONFIG.headers},
    method: 'PUT',
    body: JSON.stringify({
      role: slugNewRole
    })
  })

export const deleteMember = (apiUrl, idWorkspace, idMember) =>
  fetch(`${apiUrl}/workspaces/${idWorkspace}/members/${idMember}`, {
    credentials: 'include',
    headers: {...FETCH_CONFIG.headers},
    method: 'DELETE'
  })

export const getMyselfKnownMember = (apiUrl, userNameToSearch, idWorkspaceToExclude) =>
  fetch(`${apiUrl}/users/me/known_members?acp=${userNameToSearch}&exclude_workspace_ids=${idWorkspaceToExclude}`, {
    credentials: 'include',
    headers: {...FETCH_CONFIG.headers},
    method: 'GET'
  })

export const postWorkspaceMember = (apiUrl, idWorkspace, newMember) =>
  fetch(`${apiUrl}/workspaces/${idWorkspace}/members`, {
    credentials: 'include',
    headers: {...FETCH_CONFIG.headers},
    method: 'POST',
    body: JSON.stringify({
      user_id: newMember.id || null,
      user_email: newMember.email || null,
      user_public_name: newMember.publicName || null,
      role: newMember.role
    })
  })

export const deleteWorkspace = (apiUrl, idWorkspace) =>
  fetch(`${apiUrl}/workspaces/${idWorkspace}/trashed`, {
    credentials: 'include',
    headers: {...FETCH_CONFIG.headers},
    method: 'PUT'
  })
