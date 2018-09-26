import React from 'react'
import {ROLE} from '../../helper.js'

require('./UserStatus.styl')

// @TODO Côme - 2018/08/07 - since api yet doesn't handle notification subscriptions, this file is WIP
export const UserStatus = props => {
  const mySelf = props.curWs.memberList.find(m => m.id === props.user.user_id) || {role: ''}
  const myRole = ROLE.find(r => r.slug === mySelf.role) || {faIcon: '', hexcolor: '', label: ''}

  return (
    <div className='userstatus'>
      <div className='userstatus__role'>
        <div className='userstatus__role__msg'>
          {props.t('Hi {{name}} ! Currently, you are ', {name: props.user.public_name})}
        </div>

        <div className='userstatus__role__definition'>
          <div className='userstatus__role__definition__icon'>
            <i className={`fa fa-${myRole.faIcon}`} style={{color: myRole.hexcolor}}/>
          </div>

          <div className='userstatus__role__definition__text'>
            {props.t(myRole.label)}
          </div>
        </div>
      </div>

      <div className='userstatus__notification'>
        <div className='userstatus__notification__text'>
          {mySelf.doNotify
            ? props.t("You have subscribed to this workspace's notifications")
            : props.t("You have not subscribed to this workspace's notifications")
          }
        </div>

        {props.displayNotifBtn
          ? (
            <div className='userstatus__notification__subscribe dropdown'>
              <button
                className='userstatus__notification__subscribe__btn btn outlineTextBtn dropdown-toggle primaryColorBorder primaryColorBgHover primaryColorBorderDarken'
                type='button'
                id='dropdownMenuButton'
                data-toggle='dropdown'
                aria-haspopup='true'
                aria-expanded='false'
              >
                {mySelf.doNotify ? props.t('Subscribed') : props.t('Unsubscribed')}
              </button>

              <div className='userstatus__notification__subscribe__submenu dropdown-menu'>
                <div
                  className='userstatus__notification__subscribe__submenu__item dropdown-item primaryColorBgLightenHover'
                  onClick={props.onClickAddNotify}
                >
                  {props.t('Subscribe')}
                </div>

                <div
                  className='userstatus__notification__subscribe__submenu__item dropdown-item dropdown-item primaryColorBgLightenHover'
                  onClick={props.onClickRemoveNotify}
                >
                  {props.t('Unsubscribe')}
                </div>
              </div>
            </div>
          )
          : (
            <div
              className='userstatus__notification__btn btn outlineTextBtn primaryColorBorder primaryColorBgHover primaryColorBorderDarkenHover'
              onClick={props.onClickToggleNotifBtn}
            >
              {props.t('Change your status')}
            </div>
          )
        }
      </div>
    </div>
  )
}

export default UserStatus
