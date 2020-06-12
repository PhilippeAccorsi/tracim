import React from 'react'
import ReactDOM from 'react-dom'
import './i18n.js'
import 'core-js/stable'
import 'regenerator-runtime/runtime'
import NewMemberForm from './component/NewMemberForm/NewMemberForm.jsx'

ReactDOM.render(
  <div style={{ width: '1200px' }}>
    <NewMemberForm
      onClickCloseAddMemberBtn={() => {}}
      personalData='text'
      isEmail={false}
      onChangePersonalData={() => {}}
      searchedKnownMemberList={[]}
      autoCompleteActive={false}
      onClickKnownMember={() => {}}
      roleList={[]}
      role='woot'
      onChangeRole={() => {}}
      onClickBtnValidate={() => {}}
      emailNotifActivated
      canSendInviteNewUser
      userRoleIdInWorkspace={1}
      autoCompleteClicked={false}
      onClickAutoComplete={() => {}}
    />
  </div>
  , document.getElementById('content')
)
