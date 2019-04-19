import React from 'react'
import { connect } from 'react-redux'
import { withRouter } from 'react-router'
import i18n from '../i18n.js'
import appFactory from '../appFactory.js'
import { translate } from 'react-i18next'
import * as Cookies from 'js-cookie'
import Logo from '../component/Header/Logo.jsx'
import NavbarToggler from '../component/Header/NavbarToggler.jsx'
import MenuLinkList from '../component/Header/MenuLinkList.jsx'
import MenuActionListItemSearch from '../component/Header/MenuActionListItem/Search.jsx'
import MenuActionListItemDropdownLang from '../component/Header/MenuActionListItem/DropdownLang.jsx'
import MenuActionListItemHelp from '../component/Header/MenuActionListItem/Help.jsx'
import MenuActionListItemMenuProfil from '../component/Header/MenuActionListItem/MenuProfil.jsx'
import MenuActionListItemNotification from '../component/Header/MenuActionListItem/Notification.jsx'
import MenuActionListAdminLink from '../component/Header/MenuActionListItem/AdminLink.jsx'
import logoHeader from '../img/logo-tracim.png'
import {
  newFlashMessage,
  setUserLang,
  setUserDisconnected
} from '../action-creator.sync.js'
import {
  postUserLogout,
  putUserLang
} from '../action-creator.async.js'
import {
  COOKIE_FRONTEND,
  PAGE,
  PROFILE
} from '../helper.js'

class Header extends React.Component {
  componentDidMount () {
    i18n.changeLanguage(this.props.user.lang)
  }

  componentDidUpdate (prevProps) {
    if (prevProps.user.lang !== this.props.user.lang) i18n.changeLanguage(this.props.user.lang)
  }

  handleClickLogo = () => {
    const { props } = this

    if (props.user.logged) props.history.push(PAGE.HOME)
    else props.history.push(PAGE.LOGIN)
  }

  handleClickFeature = () => {}
  handleClickExplore = () => {}
  handleClickAbout = () => {}

  handleChangeInput = e => this.setState({inputSearchValue: e.target.value})
  handleClickSubmit = () => {}

  handleChangeLang = async idLang => {
    const { props } = this

    if (props.user.user_id === -1) {
      Cookies.set(COOKIE_FRONTEND.DEFAULT_LANGUAGE, idLang, {expires: COOKIE_FRONTEND.DEFAULT_EXPIRE_TIME})
      i18n.changeLanguage(idLang)
      props.dispatch(setUserLang(idLang))
      return
    }

    const fetchPutUserLang = await props.dispatch(putUserLang(props.user, idLang))
    switch (fetchPutUserLang.status) {
      case 200:
        i18n.changeLanguage(idLang)
        Cookies.set(COOKIE_FRONTEND.DEFAULT_LANGUAGE, idLang, {expires: COOKIE_FRONTEND.DEFAULT_EXPIRE_TIME})
        props.dispatch(setUserLang(idLang))
        props.dispatchCustomEvent('allApp_changeLang', idLang)
        break
      default: props.dispatch(newFlashMessage(props.t('Error while saving new lang'))); break
    }
  }

  handleClickHelp = () => {}

  handleClickLogout = async () => {
    const { history, dispatch, t } = this.props

    const fetchPostUserLogout = await dispatch(postUserLogout())
    if (fetchPostUserLogout.status === 204) {
      dispatch(setUserDisconnected())
      history.push(PAGE.LOGIN)
    } else {
      dispatch(newFlashMessage(t('Disconnection error', 'danger')))
    }
  }

  handleClickAgendaButton = () => {
    this.props.history.push(PAGE.AGENDA)
  }

  render () {
    const { props } = this
    const unLoggedPageList = [PAGE.LOGIN, PAGE.FORGOT_PASSWORD, PAGE.RESET_PASSWORD]

    return (
      <header className='header'>
        <nav className='navbar navbar-expand-md navbar-light bg-light'>
          <Logo logoSrc={logoHeader} onClickImg={this.handleClickLogo} />

          <div className='header__breadcrumb d-none d-lg-block ml-4' />

          <NavbarToggler />

          <div className='header__menu collapse navbar-collapse justify-content-end' id='navbarSupportedContent'>
            <MenuLinkList
              onClickFeature={this.handleClickFeature}
              onClickExplore={this.handleClickExplore}
              onClickAbout={this.handleClickAbout}
            />

            {!unLoggedPageList.includes(props.location.pathname) && !props.system.config.email_notification_activated && (
              <div className='header__menu__system' title={props.t('Email notifications are disabled')}>
                <i className='header__menu__system__icon slowblink fa fa-warning' />
                <span className='header__menu__system__text d-none d-xl-block'>
                  {props.t('Email notifications are disabled')}
                </span>
              </div>
            )}

            <ul className='header__menu__rightside'>
              <MenuActionListItemSearch
                onChangeInput={this.handleChangeInput}
                onClickSubmit={this.handleClickSubmit}
              />

              {props.user.profile === PROFILE.ADMINISTRATOR.slug && (
                <li className='header__menu__rightside__adminlink'>
                  <MenuActionListAdminLink />
                </li>
              )}

              {!unLoggedPageList.includes(props.location.pathname) && props.appList.some(a => a.slug === 'agenda') && (
                <li className='header__menu__rightside__agenda'>
                  <button
                    className='btn outlineTextBtn primaryColorBorder nohover'
                    onClick={this.handleClickAgendaButton}
                  >
                    <i className='fa fa-fw fa-calendar' />
                    {props.t('Agenda')}
                  </button>
                </li>
              )}

              <MenuActionListItemDropdownLang
                langList={props.lang}
                idLangActive={props.user.lang}
                onChangeLang={this.handleChangeLang}
              />

              <MenuActionListItemHelp
                onClickHelp={this.handleClickHelp}
              />

              <MenuActionListItemNotification />

              <MenuActionListItemMenuProfil
                user={props.user}
                onClickLogout={this.handleClickLogout}
              />
            </ul>
          </div>
        </nav>
      </header>
    )
  }
}

const mapStateToProps = ({ lang, user, system, appList }) => ({ lang, user, system, appList })
export default withRouter(connect(mapStateToProps)(translate()(appFactory(Header))))
