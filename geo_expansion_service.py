# geo_expansion_service.py
# Multi-region support and geographic expansion service

from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List
import logging

log = logging.getLogger(__name__)


class RegionService:
    """Service for managing regions and region configuration"""
    
    @staticmethod
    async def create_region(
        db: Session,
        region_code: str,
        region_name: str,
        country: str,
        timezone: str,
        currency: str,
        regulatory_framework: str,
        compliance_level: str,
        is_active: bool = True,
        created_by: Optional[int] = None
    ) -> dict:
        """
        Create a new region configuration
        
        Args:
            region_code: ISO code (US, CA, UK, etc.)
            regulatory_framework: FDIC, OCC, FINRA, FCA, etc.
            compliance_level: basic, standard, enhanced
        
        Returns:
            {"success": bool, "region_id": int}
        """
        try:
            from models import Region
            
            # Check if region already exists
            existing = db.query(Region).filter(
                Region.region_code == region_code
            ).first()
            
            if existing:
                return {"success": False, "error": "Region already exists"}
            
            region = Region(
                region_code=region_code,
                region_name=region_name,
                country=country,
                timezone=timezone,
                currency=currency,
                regulatory_framework=regulatory_framework,
                compliance_level=compliance_level,
                is_active=is_active,
                created_by=created_by,
                created_at=datetime.utcnow()
            )
            
            db.add(region)
            db.commit()
            db.refresh(region)
            
            log.info(f"Region created: {region_code} - {region_name}")
            
            return {
                "success": True,
                "region_id": region.id,
                "region_code": region_code,
                "region_name": region_name
            }
        except Exception as e:
            db.rollback()
            log.error(f"Error creating region: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def get_region(
        db: Session,
        region_code: str
    ) -> dict:
        """
        Get region configuration by code
        
        Returns:
            {"success": bool, "region": {...}}
        """
        try:
            from models import Region
            
            region = db.query(Region).filter(
                Region.region_code == region_code,
                Region.is_active == True
            ).first()
            
            if not region:
                return {"success": False, "error": "Region not found"}
            
            return {
                "success": True,
                "region": {
                    "region_id": region.id,
                    "region_code": region.region_code,
                    "region_name": region.region_name,
                    "country": region.country,
                    "timezone": region.timezone,
                    "currency": region.currency,
                    "regulatory_framework": region.regulatory_framework,
                    "compliance_level": region.compliance_level,
                    "is_active": region.is_active
                }
            }
        except Exception as e:
            log.error(f"Error fetching region: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def list_regions(db: Session) -> dict:
        """
        Get all active regions
        
        Returns:
            {"success": bool, "regions": [...]}
        """
        try:
            from models import Region
            
            regions = db.query(Region).filter(
                Region.is_active == True
            ).all()
            
            return {
                "success": True,
                "region_count": len(regions),
                "regions": [
                    {
                        "region_id": r.id,
                        "region_code": r.region_code,
                        "region_name": r.region_name,
                        "country": r.country,
                        "timezone": r.timezone,
                        "currency": r.currency,
                        "regulatory_framework": r.regulatory_framework,
                        "compliance_level": r.compliance_level
                    }
                    for r in regions
                ]
            }
        except Exception as e:
            log.error(f"Error listing regions: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def update_region(
        db: Session,
        region_code: str,
        **kwargs
    ) -> dict:
        """
        Update region configuration
        
        Returns:
            {"success": bool, "region_id": int}
        """
        try:
            from models import Region
            
            region = db.query(Region).filter(
                Region.region_code == region_code
            ).first()
            
            if not region:
                return {"success": False, "error": "Region not found"}
            
            # Update allowed fields
            allowed_fields = ['region_name', 'timezone', 'compliance_level', 'is_active']
            for field, value in kwargs.items():
                if field in allowed_fields:
                    setattr(region, field, value)
            
            db.commit()
            
            log.info(f"Region updated: {region_code}")
            
            return {
                "success": True,
                "region_id": region.id,
                "region_code": region_code
            }
        except Exception as e:
            db.rollback()
            log.error(f"Error updating region: {e}")
            return {"success": False, "error": str(e)}


class ComplianceService:
    """Service for managing region-specific compliance rules"""
    
    @staticmethod
    async def get_compliance_requirements(
        db: Session,
        region_code: str
    ) -> dict:
        """
        Get compliance requirements for region
        
        Returns:
            {"success": bool, "requirements": {...}}
        """
        try:
            from models import Region, RegionCompliance
            
            region = db.query(Region).filter(
                Region.region_code == region_code
            ).first()
            
            if not region:
                return {"success": False, "error": "Region not found"}
            
            compliance = db.query(RegionCompliance).filter(
                RegionCompliance.region_id == region.id
            ).first()
            
            if not compliance:
                return {"success": False, "error": "Compliance requirements not found"}
            
            return {
                "success": True,
                "compliance": {
                    "region_code": region_code,
                    "kyc_required": compliance.kyc_required,
                    "kyc_level": compliance.kyc_level,
                    "aml_threshold": compliance.aml_threshold,
                    "ctf_required": compliance.ctf_required,
                    "data_residency": compliance.data_residency,
                    "encryption_required": compliance.encryption_required,
                    "audit_logging_required": compliance.audit_logging_required,
                    "reporting_frequency": compliance.reporting_frequency
                }
            }
        except Exception as e:
            log.error(f"Error getting compliance requirements: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def check_account_compliance(
        db: Session,
        account_id: int,
        region_code: str
    ) -> dict:
        """
        Check if account meets region compliance requirements
        
        Returns:
            {"success": bool, "compliant": bool, "issues": [...]}
        """
        try:
            from models import Account, Region, RegionCompliance, KYCInfo
            
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                return {"success": False, "error": "Account not found"}
            
            region = db.query(Region).filter(
                Region.region_code == region_code
            ).first()
            if not region:
                return {"success": False, "error": "Region not found"}
            
            compliance = db.query(RegionCompliance).filter(
                RegionCompliance.region_id == region.id
            ).first()
            
            issues = []
            
            # Check KYC requirement
            if compliance.kyc_required:
                kyc = db.query(KYCInfo).filter(
                    KYCInfo.user_id == account.owner_id
                ).first()
                
                if not kyc or kyc.kyc_status != "approved":
                    issues.append(f"KYC {compliance.kyc_level} required")
            
            # Check data residency
            if compliance.data_residency:
                if account.region != region_code:
                    issues.append(f"Data must reside in {region_code}")
            
            compliant = len(issues) == 0
            
            log.info(f"Compliance check: Account {account_id} in {region_code} - Compliant: {compliant}")
            
            return {
                "success": True,
                "account_id": account_id,
                "region_code": region_code,
                "compliant": compliant,
                "issues": issues
            }
        except Exception as e:
            log.error(f"Error checking compliance: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def enforce_data_residency(
        db: Session,
        account_id: int,
        target_region: str
    ) -> dict:
        """
        Enforce data residency for account (mark data location)
        
        Returns:
            {"success": bool, "account_id": int}
        """
        try:
            from models import Account
            
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                return {"success": False, "error": "Account not found"}
            
            account.region = target_region
            db.commit()
            
            log.info(f"Data residency enforced: Account {account_id} → {target_region}")
            
            return {
                "success": True,
                "account_id": account_id,
                "region": target_region
            }
        except Exception as e:
            db.rollback()
            log.error(f"Error enforcing data residency: {e}")
            return {"success": False, "error": str(e)}


class RegionRoutingService:
    """Service for routing requests to correct region"""
    
    @staticmethod
    async def get_account_region(
        db: Session,
        account_id: int
    ) -> dict:
        """
        Get region for account
        
        Returns:
            {"success": bool, "region_code": str}
        """
        try:
            from models import Account
            
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                return {"success": False, "error": "Account not found"}
            
            region_code = account.region or "US"  # Default to US if not set
            
            return {
                "success": True,
                "account_id": account_id,
                "region_code": region_code
            }
        except Exception as e:
            log.error(f"Error getting account region: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def route_transaction(
        db: Session,
        account_id: int,
        transaction_amount: float,
        transaction_type: str
    ) -> dict:
        """
        Route transaction to correct region processor
        
        Returns:
            {"success": bool, "region_code": str, "processor": str}
        """
        try:
            from models import Account
            
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                return {"success": False, "error": "Account not found"}
            
            region_code = account.region or "US"
            
            # Determine processor based on region
            processor_mapping = {
                "US": "domestic_ach",
                "CA": "canadian_eft",
                "UK": "faster_payments",
                "EU": "sepa",
                "AU": "bpay"
            }
            
            processor = processor_mapping.get(region_code, "international_swift")
            
            log.info(f"Transaction routed: {transaction_type} → {region_code} ({processor})")
            
            return {
                "success": True,
                "account_id": account_id,
                "region_code": region_code,
                "processor": processor,
                "amount": transaction_amount,
                "transaction_type": transaction_type
            }
        except Exception as e:
            log.error(f"Error routing transaction: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def check_region_availability(
        db: Session,
        region_code: str,
        service_type: str
    ) -> dict:
        """
        Check if service is available in region
        
        Returns:
            {"success": bool, "available": bool}
        """
        try:
            from models import RegionService
            
            service = db.query(RegionService).filter(
                RegionService.region_code == region_code,
                RegionService.service_name == service_type
            ).first()
            
            if not service:
                return {
                    "success": True,
                    "region_code": region_code,
                    "service_type": service_type,
                    "available": False,
                    "reason": "Service not available in this region"
                }
            
            available = service.is_available
            
            return {
                "success": True,
                "region_code": region_code,
                "service_type": service_type,
                "available": available,
                "launch_date": service.launch_date.isoformat() if service.launch_date else None
            }
        except Exception as e:
            log.error(f"Error checking region availability: {e}")
            return {"success": False, "error": str(e)}
