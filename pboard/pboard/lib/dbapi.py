# -*- coding: utf-8 -*-
"""
"""
import os
from datetime import datetime
from hashlib import sha256

from sqlalchemy import Table, ForeignKey, Column
from sqlalchemy.types import Unicode, Integer, DateTime, Text
from sqlalchemy.orm import relation, synonym
from sqlalchemy.orm import joinedload_all

from pboard.model import DeclarativeBase, metadata, DBSession
from pboard.model import data as pbmd
from pboard.model import auth as pbma
import pboard.model as pbm

import tg

FIXME_ERROR_CODE=-1
class PODStaticController(object):

  @classmethod
  def getCurrentUser(cls):
    loCurrentUser = pbma.User.by_email_address(tg.request.identity['repoze.who.userid'])
    return loCurrentUser

  @classmethod
  def getUserByEmailAddress(cls, psEmailAddress):
    loUser = pbma.User.by_email_address(psEmailAddress)
    return loUser
  
  @classmethod
  def createUser(cls):
    loUser = pbma.User()
    return loUser
  
  @classmethod
  def getGroup(cls, psGroupName):
    loGroup = pbma.Group.by_group_name(psGroupName)
    return loGroup


class PODUserFilteredApiController(object):
  
  def __init__(self, piUserId, piExtraUserIdList=[]):
    self._iCurrentUserId       = piUserId
    self._iExtraUserIdList     = piExtraUserIdList
    self._iUserIdFilteringList = None
  

  def _getUserIdListForFiltering(self):
    if self._iUserIdFilteringList==None:
      self._iUserIdFilteringList = list()
      self._iUserIdFilteringList.append(self._iCurrentUserId)
      for liUserId in self._iExtraUserIdList:
        self._iUserIdFilteringList.append(liUserId)
    return self._iUserIdFilteringList


  def createNode(self):
    loNode          = pbmd.PBNode()
    loNode.owner_id = self._iCurrentUserId
    DBSession.add(loNode)
    return loNode
  
    query.filter(User.name.in_(['ed', 'wendy', 'jack']))


  def createDummyNode(self):
    loNewNode = self.createNode()
    loNewNode.data_label   = 'New document'
    loNewNode.data_content = 'insert content...'
    return loNewNode


  def getNode(self, liNodeId):
    liOwnerIdList = self._getUserIdListForFiltering()
    if liNodeId==0:
      return DBSession.query(pbmd.PBNode).options(joinedload_all("_lAllChildren")).filter(pbmd.PBNode.owner_id.in_(liOwnerIdList)).first()
    else:
      return DBSession.query(pbmd.PBNode).options(joinedload_all("_lAllChildren")).filter(pbmd.PBNode.node_id==liNodeId).filter(pbmd.PBNode.owner_id.in_(liOwnerIdList)).one()


  def getLastModifiedNodes(self, piMaxNodeNb):
    """
    Returns a list of nodes order by modification time and limited to piMaxNodeNb nodes
    """
    liOwnerIdList = self._getUserIdListForFiltering()
    return DBSession.query(pbmd.PBNode).options(joinedload_all("_lAllChildren")).filter(pbmd.PBNode.owner_id.in_(liOwnerIdList)).order_by(pbmd.PBNode.updated_at.desc()).limit(piMaxNodeNb).all()


  def getNodesByStatus(self, psNodeStatus, piMaxNodeNb=5):
    liOwnerIdList = self._getUserIdListForFiltering()
    return DBSession.query(pbmd.PBNode).options(joinedload_all("_lAllChildren")).filter(pbmd.PBNode.owner_id.in_(liOwnerIdList)).filter(pbmd.PBNode.node_status==psNodeStatus).order_by(pbmd.PBNode.updated_at).limit(piMaxNodeNb).all()


  def buildTreeListForMenu(self):
    liOwnerIdList = self._getUserIdListForFiltering()
    
    loNodeList = pbm.DBSession.query(pbmd.PBNode).filter(pbmd.PBNode.owner_id.in_(liOwnerIdList)).filter(pbmd.PBNode.node_type==pbmd.PBNodeType.Data).order_by(pbmd.PBNode.parent_tree_path).order_by(pbmd.PBNode.node_order).order_by(pbmd.PBNode.node_id).all()
    loTreeList = []
    loTmpDict = {}
    for loNode in loNodeList:
      loTmpDict[loNode.node_id] = loNode
  
      if loNode.parent_id==None:
        loTreeList.append(loNode)
      else:
        # append the node to the parent list
        # FIXME - D.A - 2013-10-08
        # The following line may raise an exception
        # We suppose that the parent node has already been added
        # this *should* be the case, but the code does not check it
        if loNode.parent_id in loTmpDict.keys():
          loTmpDict[loNode.parent_id] = self.getNode(loNode.parent_id)
        loTmpDict[loNode.parent_id].appendStaticChild(loNode)
  
    return loTreeList

  def getParentNode(self, loNode):
    liOwnerIdList = self._getUserIdListForFiltering()
    return DBSession.query(pbmd.PBNode).filter(pbmd.PBNode.owner_id.in_(liOwnerIdList)).filter(pbmd.PBNode.node_id==loNode.parent_id).one()

  def getSiblingNodes(self, poNode, pbReverseOrder=False):
    liOwnerIdList = self._getUserIdListForFiltering()
    
    if pbReverseOrder:
      return DBSession.query(pbmd.PBNode).filter(pbmd.PBNode.owner_id.in_(liOwnerIdList)).filter(pbmd.PBNode.parent_id==poNode.parent_id).order_by(pbmd.PBNode.node_order.desc()).all()
    else:
      return DBSession.query(pbmd.PBNode).filter(pbmd.PBNode.owner_id.in_(liOwnerIdList)).filter(pbmd.PBNode.parent_id==poNode.parent_id).order_by(pbmd.PBNode.node_order).all()

  def resetNodeOrderOfSiblingNodes(self, loSiblingNodes):
    liNewWeight = 0
    for loNode in loSiblingNodes:
      liNewWeight = liNewWeight + 1
      loNode.node_order = liNewWeight
    # DBSession.save()

  def moveNodeUpper(self, loNode):
    # FIXME - manage errors and logging
    
    loSiblingNodes = self.getSiblingNodes(loNode)
    self.resetNodeOrderOfSiblingNodes(loSiblingNodes)
  
    loPreviousItem = None
    for loItem in loSiblingNodes:
      if loItem==loNode:
        if loPreviousItem==None:
          return FIXME_ERROR_CODE # FIXME - D.A. Do not use hard-coded error codes
          print("No previous node")
        else:
          liPreviousItemOrder       = loPreviousItem.node_order
          loPreviousItem.node_order = loNode.node_order
          loNode.node_order         = liPreviousItemOrder
          # DBSession.save()
          break
      loPreviousItem = loItem

  def moveNodeLower(self, loNode):
    # FIXME - manage errors and logging
    
    loSiblingNodes = self.getSiblingNodes(loNode)
    self.resetNodeOrderOfSiblingNodes(loSiblingNodes)
  
    loPreviousItem = None
    for loItem in reversed(loSiblingNodes):
      if loItem==loNode:
        if loPreviousItem==None:
          return FIXME_ERROR_CODE # FIXME - D.A. Do not use hard-coded error codes
          # FIXME
          print("No previous node")
        else:
          liPreviousItemOrder       = loPreviousItem.node_order
          loPreviousItem.node_order = loNode.node_order
          loNode.node_order         = liPreviousItemOrder
          # DBSession.save()
          break
      loPreviousItem = loItem

  def getNodeFileContent(self, liNodeId):
    liOwnerIdList = self._getUserIdListForFiltering()
    return DBSession.query(pbmd.PBNode).filter(pbmd.PBNode.owner_id.in_(liOwnerIdList)).filter(pbmd.PBNode.node_id==liNodeId).one().data_file_content

  def deleteNode(loNode):
    # INFO - D.A. - 2013-11-07 - should be save as getNode should return only accessible nodes
    DBSession.delete(loNode)
    return
