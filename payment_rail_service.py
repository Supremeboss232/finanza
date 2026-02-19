"""
Payment Rail Service - Abstraction for all payment types (ACH, Wire, RTP, FedNow)
Handles transaction routing to appropriate payment infrastructure
"""

from datetime import datetime, date, timedelta
from enum import Enum
from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from models import (
    Transaction, Settlement, SettlementState, ACHFile, ACHEntry,
    WireTransfer, RTPTransaction, FedNowTransaction, Account
)
import logging

log = logging.getLogger(__name__)


class PaymentRail(str, Enum):
    """Payment rail types"""
    ACH = "ACH"
    WIRE = "Wire"
    RTP = "RTP"
    FEDNOW = "FedNow"
    INTERNAL = "Internal"


class SettlementState(str, Enum):
    """Settlement workflow states"""
    INITIATED = "initiated"
    VALIDATED = "validated"
    BATCHED = "batched"
    SUBMITTED = "submitted"
    IN_TRANSIT = "in_transit"
    SETTLED = "settled"
    FAILED = "failed"
    RETURNED = "returned"


class PaymentRailService:
    """Main payment routing and settlement service"""
    
    @staticmethod
    async def determine_rail(amount: float, urgency: str = "normal") -> PaymentRail:
        """
        Determine optimal payment rail based on transaction characteristics
        
        Rules:
        - < $0.5M, urgent → RTP or FedNow
        - < $0.5M, normal → ACH
        - > $0.5M, any → Wire
        - Same-day needed → RTP/FedNow/Wire
        """
        if urgency == "urgent" or urgency == "immediate":
            if amount < 500000:
                return PaymentRail.RTP  # or FedNow
            else:
                return PaymentRail.WIRE
        else:
            if amount >= 500000:
                return PaymentRail.WIRE
            else:
                return PaymentRail.ACH
    
    @staticmethod
    async def route_transaction(
        db: Session,
        transaction_id: int,
        rail: PaymentRail,
        receiving_bank: Optional[str] = None,
        receiving_routing: Optional[str] = None,
        receiving_account: Optional[str] = None
    ) -> Dict:
        """Route transaction to appropriate payment rail"""
        
        try:
            transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
            if not transaction:
                return {"success": False, "error": "Transaction not found"}
            
            # Create settlement record
            settlement = Settlement(
                transaction_id=transaction_id,
                rail_type=rail.value,
                status="pending"
            )
            db.add(settlement)
            
            # Initialize state machine
            settlement_state = SettlementState(
                transaction_id=transaction_id,
                current_state=SettlementState.INITIATED.value,
                metadata=f'{{"rail": "{rail.value}", "initiated_at": "{datetime.utcnow().isoformat()}"}}'
            )
            db.add(settlement_state)
            db.flush()
            
            # Route to appropriate rail
            if rail == PaymentRail.ACH:
                result = await ACHService.prepare_transfer(db, transaction_id)
            elif rail == PaymentRail.WIRE:
                result = await WireService.prepare_transfer(
                    db, transaction_id, 
                    receiving_bank, receiving_routing, receiving_account
                )
            elif rail == PaymentRail.RTP:
                result = await RTPService.prepare_transfer(db, transaction_id)
            elif rail == PaymentRail.FEDNOW:
                result = await FedNowService.prepare_transfer(db, transaction_id)
            elif rail == PaymentRail.INTERNAL:
                result = await InternalTransferService.complete_transfer(db, transaction_id)
            
            db.commit()
            log.info(f"Transaction {transaction_id} routed to {rail.value}")
            return result
            
        except Exception as e:
            db.rollback()
            log.error(f"Error routing transaction {transaction_id}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def update_settlement_state(
        db: Session,
        transaction_id: int,
        new_state: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Update settlement state machine"""
        try:
            state = db.query(SettlementState).filter(
                SettlementState.transaction_id == transaction_id
            ).first()
            
            if state:
                state.previous_state = state.current_state
                state.current_state = new_state
                state.transition_time = datetime.utcnow()
                if metadata:
                    import json
                    state.state_metadata = json.dumps(metadata)
                db.commit()
                return True
            return False
        except Exception as e:
            log.error(f"Error updating settlement state: {str(e)}")
            return False


class ACHService:
    """ACH (Automated Clearing House) payment service"""
    
    # ACH operates in batches - typically settle T+1
    STANDARD_SETTLEMENT_DAYS = 1
    
    @staticmethod
    async def prepare_transfer(db: Session, transaction_id: int) -> Dict:
        """Prepare ACH transfer for batching"""
        try:
            transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
            if not transaction:
                return {"success": False, "error": "Transaction not found"}
            
            # Create ACH entry
            ach_entry = ACHEntry(
                transaction_id=transaction_id,
                entry_type="debit",
                account_number=transaction.sender_account.account_number,
                amount=transaction.amount,
                description=transaction.description or f"ACH Transfer {transaction_id}",
                status="pending"
            )
            db.add(ach_entry)
            db.flush()
            
            # Update settlement
            settlement = db.query(Settlement).filter(
                Settlement.transaction_id == transaction_id
            ).first()
            if settlement:
                settlement.settlement_date = date.today() + timedelta(days=self.STANDARD_SETTLEMENT_DAYS)
                settlement.status = "pending"
            
            db.commit()
            log.info(f"ACH entry {ach_entry.id} created for transaction {transaction_id}")
            return {"success": True, "ach_entry_id": ach_entry.id}
        except Exception as e:
            db.rollback()
            log.error(f"Error preparing ACH transfer: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def batch_transactions(db: Session, effective_date: date) -> Dict:
        """Create ACH file batch for submission to Federal Reserve"""
        try:
            # Get all pending ACH entries for this date
            entries = db.query(ACHEntry).filter(
                ACHEntry.status == "pending",
                ACHEntry.ach_file_id.is_(None)
            ).all()
            
            if not entries:
                return {"success": True, "message": "No pending entries to batch"}
            
            # Create ACH file
            batch_number = db.query(ACHFile).count() + 1
            file_id = f"ACH{datetime.utcnow().strftime('%Y%m%d')}{batch_number:06d}"
            
            ach_file = ACHFile(
                file_id=file_id,
                batch_number=batch_number,
                effective_date=effective_date,
                status="pending",
                total_amount=sum(e.amount for e in entries),
                total_entries=len(entries),
                transmission_date=datetime.utcnow()
            )
            db.add(ach_file)
            db.flush()
            
            # Assign entries to file
            for entry in entries:
                entry.ach_file_id = ach_file.id
                entry.status = "batched"
            
            db.commit()
            log.info(f"ACH file {file_id} created with {len(entries)} entries")
            return {
                "success": True,
                "file_id": file_id,
                "batch_number": batch_number,
                "entry_count": len(entries),
                "total_amount": ach_file.total_amount
            }
        except Exception as e:
            db.rollback()
            log.error(f"Error batching ACH transactions: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def submit_to_fed(db: Session, file_id: str) -> Dict:
        """Submit ACH file to Federal Reserve (mock - would call actual Fed API)"""
        try:
            ach_file = db.query(ACHFile).filter(ACHFile.file_id == file_id).first()
            if not ach_file:
                return {"success": False, "error": "File not found"}
            
            # TODO: Call actual Federal Reserve ACH API
            # For now, mark as transmitted
            ach_file.status = "transmitted"
            db.commit()
            
            log.info(f"ACH file {file_id} submitted to Federal Reserve")
            return {"success": True, "status": "transmitted"}
        except Exception as e:
            log.error(f"Error submitting ACH to Fed: {str(e)}")
            return {"success": False, "error": str(e)}


class WireService:
    """Wire transfer service"""
    
    # Wire transfers typically settle same-day
    STANDARD_SETTLEMENT_HOURS = 4
    
    @staticmethod
    async def prepare_transfer(
        db: Session,
        transaction_id: int,
        receiving_bank: str,
        receiving_routing: str,
        receiving_account: str
    ) -> Dict:
        """Prepare wire transfer for Fedwire submission"""
        try:
            transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
            if not transaction:
                return {"success": False, "error": "Transaction not found"}
            
            # Validate wire details
            if not receiving_routing or len(receiving_routing) != 9:
                return {"success": False, "error": "Invalid routing number"}
            
            wire = WireTransfer(
                transaction_id=transaction_id,
                receiving_bank=receiving_bank,
                receiving_routing=receiving_routing,
                receiving_account=receiving_account,
                amount=transaction.amount,
                fee=0.0,  # TODO: Calculate based on wire type
                status="pending"
            )
            db.add(wire)
            db.flush()
            
            # Update settlement
            settlement = db.query(Settlement).filter(
                Settlement.transaction_id == transaction_id
            ).first()
            if settlement:
                settlement.settlement_time = datetime.utcnow() + timedelta(hours=self.STANDARD_SETTLEMENT_HOURS)
                settlement.status = "pending"
            
            db.commit()
            log.info(f"Wire transfer {wire.id} created for transaction {transaction_id}")
            return {"success": True, "wire_id": wire.id}
        except Exception as e:
            db.rollback()
            log.error(f"Error preparing wire transfer: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def submit_to_fedwire(db: Session, wire_id: int) -> Dict:
        """Submit wire to Federal Reserve Fedwire system"""
        try:
            wire = db.query(WireTransfer).filter(WireTransfer.id == wire_id).first()
            if not wire:
                return {"success": False, "error": "Wire not found"}
            
            # TODO: Call actual Fedwire API
            # For now, generate reference
            wire.fedwire_reference = f"FW{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{wire_id}"
            wire.status = "transmitted"
            db.commit()
            
            log.info(f"Wire {wire_id} submitted to Fedwire: {wire.fedwire_reference}")
            return {"success": True, "fedwire_reference": wire.fedwire_reference}
        except Exception as e:
            log.error(f"Error submitting wire to Fedwire: {str(e)}")
            return {"success": False, "error": str(e)}


class RTPService:
    """Real-Time Payments service"""
    
    # RTP clears within hours
    STANDARD_SETTLEMENT_HOURS = 2
    
    @staticmethod
    async def prepare_transfer(db: Session, transaction_id: int) -> Dict:
        """Prepare RTP transfer"""
        try:
            transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
            if not transaction:
                return {"success": False, "error": "Transaction not found"}
            
            rtp = RTPTransaction(
                transaction_id=transaction_id,
                rtp_id=f"RTP{transaction_id}{datetime.utcnow().timestamp()}",
                amount=transaction.amount,
                status="pending"
            )
            db.add(rtp)
            db.flush()
            
            settlement = db.query(Settlement).filter(
                Settlement.transaction_id == transaction_id
            ).first()
            if settlement:
                settlement.settlement_time = datetime.utcnow() + timedelta(hours=self.STANDARD_SETTLEMENT_HOURS)
            
            db.commit()
            log.info(f"RTP {rtp.id} created for transaction {transaction_id}")
            return {"success": True, "rtp_id": rtp.id}
        except Exception as e:
            db.rollback()
            log.error(f"Error preparing RTP transfer: {str(e)}")
            return {"success": False, "error": str(e)}


class FedNowService:
    """Federal Reserve FedNow instant payment service"""
    
    # FedNow settles instantly (within seconds)
    STANDARD_SETTLEMENT_SECONDS = 30
    
    @staticmethod
    async def prepare_transfer(db: Session, transaction_id: int) -> Dict:
        """Prepare FedNow transfer"""
        try:
            transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
            if not transaction:
                return {"success": False, "error": "Transaction not found"}
            
            fednow = FedNowTransaction(
                transaction_id=transaction_id,
                fednow_id=f"FN{transaction_id}{datetime.utcnow().timestamp()}",
                amount=transaction.amount,
                status="pending"
            )
            db.add(fednow)
            db.flush()
            
            settlement = db.query(Settlement).filter(
                Settlement.transaction_id == transaction_id
            ).first()
            if settlement:
                settlement.settlement_time = datetime.utcnow() + timedelta(seconds=self.STANDARD_SETTLEMENT_SECONDS)
            
            db.commit()
            log.info(f"FedNow {fednow.id} created for transaction {transaction_id}")
            return {"success": True, "fednow_id": fednow.id}
        except Exception as e:
            db.rollback()
            log.error(f"Error preparing FedNow transfer: {str(e)}")
            return {"success": False, "error": str(e)}


class InternalTransferService:
    """Internal transfer service (within same bank)"""
    
    @staticmethod
    async def complete_transfer(db: Session, transaction_id: int) -> Dict:
        """Complete internal transfer immediately"""
        try:
            transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
            if not transaction:
                return {"success": False, "error": "Transaction not found"}
            
            # Update both accounts immediately
            if transaction.sender_account:
                transaction.sender_account.balance -= transaction.amount
            if transaction.receiver_account:
                transaction.receiver_account.balance += transaction.amount
            
            # Mark settlement as complete
            settlement = db.query(Settlement).filter(
                Settlement.transaction_id == transaction_id
            ).first()
            if settlement:
                settlement.status = "settled"
                settlement.settlement_date = date.today()
                settlement.settlement_time = datetime.utcnow()
            
            # Mark transaction complete
            transaction.status = "completed"
            
            db.commit()
            log.info(f"Internal transfer {transaction_id} completed immediately")
            return {"success": True, "status": "settled"}
        except Exception as e:
            db.rollback()
            log.error(f"Error completing internal transfer: {str(e)}")
            return {"success": False, "error": str(e)}
