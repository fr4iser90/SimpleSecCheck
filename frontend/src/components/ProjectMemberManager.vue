<template>
  <div class="project-member-manager">
    <h4>Manage Project Members</h4>

    <div v-if="isLoadingProjectDetails || isLoadingMembers || isLoadingUsers" class="loading-message">Loading member management data...</div>
    <div v-if="projectLoadError" class="error-message">Error loading project details: {{ projectLoadError }}</div>
    <div v-if="membersLoadError" class="error-message">Error loading members: {{ membersLoadError }}</div>
    <div v-if="usersLoadError" class="error-message">Error loading users: {{ usersLoadError }}</div>
    
    <div v-if="!canManageMembers && project && !isLoadingProjectDetails" class="alert alert-warning">
      Your role ({{ currentUserRoleInProject || 'N/A' }}) does not permit managing members for this project. (Requires Manager or Owner).
    </div>

    <div v-if="project && canManageMembers">
      <!-- Add Member Form -->
      <div class="add-member-form card mb-3">
        <div class="card-body">
          <h5 class="card-title">Add New Member</h5>
          <form @submit.prevent="handleAddMember">
            <div class="form-group">
              <label for="selectUser">User:</label>
              <select id="selectUser" v-model="addMemberForm.userId" class="form-control" required>
                <option :value="null" disabled>-- Select User --</option>
                <option v-for="user in availableUsers" :key="user.id" :value="user.id">
                  {{ user.username }} ({{ user.email }})
                </option>
              </select>
            </div>
            <div class="form-group">
              <label for="selectRole">Role:</label>
              <select id="selectRole" v-model="addMemberForm.role" class="form-control" required>
                <option value="viewer">Viewer</option>
                <option value="developer">Developer</option>
                <option value="manager">Manager</option>
              </select>
            </div>
            <button type="submit" class="btn btn-success" :disabled="isSubmittingAdd">
              {{ isSubmittingAdd ? 'Adding...' : 'Add Member' }}
            </button>
            <div v-if="addMemberError" class="error-message mt-2">{{ addMemberError }}</div>
          </form>
        </div>
      </div>

      <!-- Current Members List -->
      <h5>Current Members ({{memberships.length}})</h5>
      <ul v-if="memberships.length > 0" class="list-group">
        <li v-for="membership in memberships" :key="membership.id" class="list-group-item">
          <div class="d-flex justify-content-between align-items-center">
            <div>
              <strong>{{ membership.user.username }}</strong> ({{ membership.user.email }})
              <span class="badge ml-2" :class="getRoleClass(membership.role)">{{ membership.role }}</span>
            </div>
            <div v-if="membership.user.id !== currentUser.id && project.owner.id !== membership.user.id"> <!-- Cannot edit self or owner directly here -->
              <select v-model="editMemberForm[membership.id]" class="form-control-sm mr-2" @change="handleRoleChange(membership, $event.target.value)">
                <option value="viewer" :selected="membership.role === 'viewer'">Viewer</option>
                <option value="developer" :selected="membership.role === 'developer'">Developer</option>
                <option value="manager" :selected="membership.role === 'manager'">Manager</option>
              </select>
              <button @click="confirmRemoveMember(membership)" class="btn btn-sm btn-danger" :disabled="isSubmittingUpdate[membership.id] || isSubmittingRemove[membership.id]">
                <span v-if="isSubmittingRemove[membership.id]">Removing...</span>
                <span v-else>Remove</span>
              </button>
              <div v-if="updateMemberError[membership.id]" class="error-message-inline text-danger small">{{ updateMemberError[membership.id] }}</div>
            </div>
             <div v-else>
                <small class="text-muted mr-2"> 
                    <span v-if="project.owner.id === membership.user.id">(Project Owner)</span>
                    <span v-else-if="membership.user.id === currentUser.id">(Yourself)</span>
                </small>
            </div>
          </div>
        </li>
      </ul>
      <p v-else>No members (other than the owner) have been added to this project yet.</p>
    </div>

    <!-- Delete Confirmation Modal -->
    <div v-if="showRemoveConfirmModal && memberToRemove" class="modal-backdrop">
       <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Confirm Removal</h5>
            <button type="button" class="close" @click="cancelRemoveMember">&times;</button>
          </div>
          <div class="modal-body">
            <p>Are you sure you want to remove <strong>{{ memberToRemove.user.username }}</strong> from this project?</p>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="cancelRemoveMember">Cancel</button>
            <button type="button" class="btn btn-danger" @click="executeRemoveMember" :disabled="isSubmittingRemove[memberToRemove.id]">
              {{ isSubmittingRemove[memberToRemove.id] ? 'Removing...' : 'Remove' }}
            </button>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script>
import api from '../services/api';

export default {
  name: 'ProjectMemberManager',
  props: {
    projectId: {
      type: [Number, String],
      required: true,
    },
    currentUser: {
      type: Object,
      required: true,
    },
  },
  data() {
    return {
      project: null,
      isLoadingProjectDetails: false,
      projectLoadError: null,
      currentUserRoleInProject: null,

      memberships: [],
      isLoadingMembers: false,
      membersLoadError: null,

      allUsers: [],
      isLoadingUsers: false,
      usersLoadError: null,

      addMemberForm: {
        userId: null,
        role: 'viewer',
      },
      isSubmittingAdd: false,
      addMemberError: null,

      // For inline editing - stores the selected role for each member being edited
      editMemberForm: {}, // { membershipId: newRole } 
      isSubmittingUpdate: {}, // { membershipId: boolean }
      updateMemberError: {}, // { membershipId: errorText }

      showRemoveConfirmModal: false,
      memberToRemove: null,
      isSubmittingRemove: {}, // { membershipId: boolean }
    };
  },
  computed: {
    canManageMembers() {
      if (!this.project || !this.currentUserRoleInProject) return false;
      return ['owner', 'manager'].includes(this.currentUserRoleInProject);
    },
    availableUsers() {
      // Filter out users already members of this project or the project owner
      const memberIds = this.memberships.map(m => m.user.id);
      if (this.project && this.project.owner) {
        memberIds.push(this.project.owner.id);
      }
      return this.allUsers.filter(user => !memberIds.includes(user.id));
    },
  },
  watch: {
    projectId: {
      immediate: true,
      async handler(newId) {
        if (newId) {
          await this.fetchProjectDetailsAndRole();
          if (this.canManageMembers || this.currentUserRoleInProject) { // Also fetch members if at least a viewer
             await this.fetchMemberships();
          }
          if (this.canManageMembers) { // Only fetch all users if manager wants to add
             await this.fetchAllUsers();
          }
        } else {
          this.resetData();
        }
      },
    },
  },
  methods: {
    resetData() {
      this.project = null;
      this.currentUserRoleInProject = null;
      this.memberships = [];
      this.allUsers = [];
      this.projectLoadError = null;
      this.membersLoadError = null;
      this.usersLoadError = null;
      this.addMemberForm = { userId: null, role: 'viewer' };
      this.addMemberError = null;
      this.editMemberForm = {};
      this.updateMemberError = {};
    },
    async fetchProjectDetailsAndRole() {
      this.isLoadingProjectDetails = true;
      this.projectLoadError = null;
      try {
        const projectData = await api.getProject(this.projectId);
        this.project = projectData;
        this.determineCurrentUserRole();
      } catch (error) {
        this.projectLoadError = 'Failed to load project details.';
        console.error('Error fetching project details:', error);
      } finally {
        this.isLoadingProjectDetails = false;
      }
    },
    determineCurrentUserRole() {
      if (!this.project || !this.currentUser || !this.currentUser.id) {
        this.currentUserRoleInProject = null;
        return;
      }
      if (this.project.owner && this.project.owner.id === this.currentUser.id) {
        this.currentUserRoleInProject = 'owner';
        return;
      }
      if (this.project.project_memberships && this.project.project_memberships.length > 0) {
        const membership = this.project.project_memberships.find(
          m => m.user.id === this.currentUser.id
        );
        this.currentUserRoleInProject = membership ? membership.role : null;
      } else {
        this.currentUserRoleInProject = null;
      }
    },
    async fetchMemberships() {
      if (!this.projectId) return;
      this.isLoadingMembers = true;
      this.membersLoadError = null;
      try {
        const data = await api.getProjectMemberships(this.projectId);
        this.memberships = data.results || data; 
        // Initialize editMemberForm for existing members
        this.memberships.forEach(m => {
            this.$set(this.editMemberForm, m.id, m.role);
            this.$set(this.isSubmittingUpdate, m.id, false);
            this.$set(this.isSubmittingRemove, m.id, false);
            this.$set(this.updateMemberError, m.id, null);
        });
      } catch (error) {
        this.membersLoadError = 'Failed to load project members.';
        console.error('Error fetching project memberships:', error);
      } finally {
        this.isLoadingMembers = false;
      }
    },
    async fetchAllUsers() {
      this.isLoadingUsers = true;
      this.usersLoadError = null;
      try {
        const data = await api.getUsers(); // Assumes this returns a list of user objects
        this.allUsers = data.results || data;
      } catch (error) {
        this.usersLoadError = 'Failed to load users list.';
        console.error('Error fetching users:', error);
      } finally {
        this.isLoadingUsers = false;
      }
    },
    async handleAddMember() {
      if (!this.addMemberForm.userId || !this.addMemberForm.role) {
        this.addMemberError = 'Please select a user and a role.';
        return;
      }
      this.isSubmittingAdd = true;
      this.addMemberError = null;
      try {
        const payload = {
          user: this.addMemberForm.userId,
          project: this.projectId,
          role: this.addMemberForm.role,
        };
        await api.addProjectMember(payload);
        await this.fetchMemberships(); // Refresh list
        this.addMemberForm.userId = null;
        this.addMemberForm.role = 'viewer';
      } catch (error) {
        this.addMemberError = error.response?.data?.detail || error.response?.data?.non_field_errors?.[0] || 'Failed to add member.';
        if (error.response?.data?.user) this.addMemberError += ` User: ${error.response.data.user.join(', ')}`;
        console.error('Error adding member:', error);
      } finally {
        this.isSubmittingAdd = false;
      }
    },
    async handleRoleChange(membership, newRole) {
      if (membership.role === newRole) return;
      this.$set(this.isSubmittingUpdate, membership.id, true);
      this.$set(this.updateMemberError, membership.id, null);
      try {
        await api.updateProjectMember(membership.id, { role: newRole });
        // Update local data to reflect change immediately
        const memberToUpdate = this.memberships.find(m => m.id === membership.id);
        if(memberToUpdate) memberToUpdate.role = newRole;
        this.editMemberForm[membership.id] = newRole; // Ensure select reflects the new role
      } catch (error) {
        this.updateMemberError[membership.id] = error.response?.data?.detail || 'Failed to update role.';
        console.error('Error updating role:', error);
        // Revert select if API call fails
        this.editMemberForm[membership.id] = membership.role; 
      } finally {
        this.$set(this.isSubmittingUpdate, membership.id, false);
      }
    },
    confirmRemoveMember(membership) {
      this.memberToRemove = membership;
      this.showRemoveConfirmModal = true;
    },
    cancelRemoveMember() {
      this.showRemoveConfirmModal = false;
      this.memberToRemove = null;
    },
    async executeRemoveMember() {
      if (!this.memberToRemove) return;
      const memberId = this.memberToRemove.id;
      this.$set(this.isSubmittingRemove, memberId, true);
      try {
        await api.removeProjectMember(memberId);
        this.memberships = this.memberships.filter(m => m.id !== memberId);
        this.cancelRemoveMember();
      } catch (error) {
        alert(`Failed to remove member: ${error.response?.data?.detail || error.message}`);
        console.error('Error removing member:', error);
        this.$set(this.isSubmittingRemove, memberId, false); // Only reset if error, success closes modal
      }
    },
    getRoleClass(role) {
      const roleClasses = {
        owner: 'badge-dark',
        manager: 'badge-primary',
        developer: 'badge-success',
        viewer: 'badge-secondary',
      };
      return roleClasses[role.toLowerCase()] || 'badge-light';
    },
  },
  async mounted() {
    // Initial data fetch triggered by watcher on projectId
  },
};
</script>

<style scoped>
.project-member-manager {
  padding: 15px;
  border: 1px solid #eee;
  border-radius: 5px;
  background-color: #fdfdfd;
}
.loading-message, .error-message, .info-message {
  padding: 10px;
  margin-bottom: 15px;
  border-radius: 4px;
}
.loading-message { background-color: #e9ecef; color: #495057; border: 1px solid #ced4da; }
.error-message { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
.info-message { background-color: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
.error-message-inline { font-size: 0.8em; }

.add-member-form {
  margin-bottom: 20px;
  padding: 15px;
  background-color: #fff;
  border: 1px solid #ddd;
}

.list-group-item {
  margin-bottom: 8px;
}

.form-control-sm {
    height: calc(1.5em + .5rem + 2px);
    padding: .25rem .5rem;
    font-size: .875rem;
    line-height: 1.5;
    border-radius: .2rem;
}
.mr-2 { margin-right: .5rem!important; }
.ml-2 { margin-left: .5rem!important; }
.mb-3 { margin-bottom: 1rem!important; }

.badge {
  font-size: 0.8em;
}
.badge-dark { background-color: #343a40; color: white; }
.badge-primary { background-color: #007bff; color: white; }
.badge-success { background-color: #28a745; color: white; }
.badge-secondary { background-color: #6c757d; color: white; }
.badge-light { background-color: #f8f9fa; color: #212529; }

/* Modal Styles (similar to ProjectConfigurations) */
.modal-backdrop {
  position: fixed; top: 0; left: 0; width: 100%; height: 100%;
  background-color: rgba(0,0,0,0.5); display: flex;
  justify-content: center; align-items: center; z-index: 1050;
}
.modal-dialog { 
  background-color: white; padding: 20px; border-radius: 5px; 
  min-width: 300px; max-width: 500px; box-shadow: 0 5px 15px rgba(0,0,0,0.5);
}
.modal-header, .modal-body, .modal-footer { padding: 1rem; }
.modal-header { border-bottom: 1px solid #dee2e6; display: flex; justify-content: space-between; align-items: center; }
.modal-footer { border-top: 1px solid #dee2e6; display: flex; justify-content: flex-end; }
.modal-footer .btn + .btn { margin-left: 0.5rem; }
.close { border: none; background: none; font-size: 1.5rem; font-weight: bold; opacity: 0.5; }
.close:hover { opacity: 0.75; }

/* Standard button styling (can be centralized) */
.btn { display: inline-block; font-weight: 400; text-align: center; vertical-align: middle; cursor: pointer; user-select: none; background-color: transparent; border: 1px solid transparent; padding: 0.375rem 0.75rem; font-size: 1rem; line-height: 1.5; border-radius: 0.25rem; }
.btn-primary { color: #fff; background-color: #007bff; border-color: #007bff; }
.btn-primary:hover { background-color: #0056b3; }
.btn-success { color: #fff; background-color: #28a745; border-color: #28a745; }
.btn-success:hover { background-color: #198754; }
.btn-danger { color: #fff; background-color: #dc3545; border-color: #dc3545; }
.btn-danger:hover { background-color: #c82333; }
.btn-secondary { color: #fff; background-color: #6c757d; border-color: #6c757d; }
.btn-secondary:hover { background-color: #545b62; }
.btn-sm { padding: 0.25rem 0.5rem; font-size: 0.875rem; }
.btn:disabled { opacity: 0.65; cursor: not-allowed; }
</style> 