"""
Database configuration for experiment history storage.

Optional SQLite database for storing experiment metadata,
results, and historical data.
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional
import logging

from .config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Database setup
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ExperimentRecord(Base):
    """Database model for experiment records."""
    
    __tablename__ = "experiments"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)  # Human-readable experiment name
    route_id = Column(String, nullable=False)
    route_name = Column(String, nullable=True)  # Human-readable route name from XML
    route_file = Column(String, nullable=False)
    search_method = Column(String, nullable=False)
    num_iterations = Column(Integer, nullable=False)
    timeout_seconds = Column(Integer, nullable=False)
    headless = Column(Boolean, default=False)
    random_seed = Column(Integer, default=42)
    reward_function = Column(String, default="ttc")
    agent = Column(String, default="ba")  # Agent type: ba (Behavior Agent) or apollo (Apollo)
    
    # Method-specific parameters
    pso_pop_size = Column(Integer, nullable=True)
    pso_w = Column(Float, nullable=True)
    pso_c1 = Column(Float, nullable=True)
    pso_c2 = Column(Float, nullable=True)
    ga_pop_size = Column(Integer, nullable=True)
    ga_prob_mut = Column(Float, nullable=True)
    
    # Status and timing
    status = Column(String, default="created")  # created, running, completed, failed, stopped
    created_at = Column(DateTime, default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Enhanced progress tracking
    current_iteration = Column(Integer, default=0)
    scenarios_executed = Column(Integer, default=0)
    total_scenarios = Column(Integer, nullable=True)
    scenarios_this_iteration = Column(Integer, default=0)
    
    # Results
    best_reward = Column(Float, nullable=True)
    total_iterations = Column(Integer, default=0)
    collision_found = Column(Boolean, default=False)
    
    # Metadata
    output_directory = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)


def create_tables():
    """Create database tables."""
    Base.metadata.create_all(bind=engine)

def migrate_database():
    """Apply database migrations for schema updates."""
    try:
        # Check if route_name column exists, if not add it
        db = SessionLocal()
        try:
            # Try to query the column - if it fails, we need to add it
            db.execute("SELECT route_name FROM experiments LIMIT 1")
            logger.info("Route name column already exists")
        except Exception:
            # Column doesn't exist, add it
            try:
                # Use text() for raw SQL in SQLAlchemy 2.0+
                from sqlalchemy import text
                db.execute(text("ALTER TABLE experiments ADD COLUMN route_name TEXT"))
                db.commit()
                logger.info("Successfully added route_name column to experiments table")
            except Exception as e:
                logger.warning(f"Failed to add route_name column: {e}")
                # Continue without the column - older experiments won't have route names
                
        # Check for other potential missing columns and add them if needed
        try:
            db.execute("SELECT total_scenarios FROM experiments LIMIT 1")
        except Exception:
            try:
                from sqlalchemy import text
                db.execute(text("ALTER TABLE experiments ADD COLUMN total_scenarios INTEGER"))
                db.commit()
                logger.info("Successfully added total_scenarios column")
            except Exception as e:
                logger.warning(f"Failed to add total_scenarios column: {e}")
                
        try:
            db.execute("SELECT scenarios_this_iteration FROM experiments LIMIT 1")
        except Exception:
            try:
                from sqlalchemy import text
                db.execute(text("ALTER TABLE experiments ADD COLUMN scenarios_this_iteration INTEGER DEFAULT 0"))
                db.commit()
                logger.info("Successfully added scenarios_this_iteration column")
            except Exception as e:
                logger.warning(f"Failed to add scenarios_this_iteration column: {e}")
                
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        # Continue anyway - the application should still work with the base schema

def init_db():
    """Initialize database."""
    create_tables()
    migrate_database()  # Run migrations after creating tables


def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Database utility functions
def save_experiment_record(
    experiment_id: str,
    name: str,
    route_id: str,
    route_file: str,
    search_method: str,
    **kwargs
) -> ExperimentRecord:
    """Save a new experiment record."""
    db = SessionLocal()
    try:
        record = ExperimentRecord(
            id=experiment_id,
            name=name,
            route_id=route_id,
            route_file=route_file,
            search_method=search_method,
            **kwargs
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    finally:
        db.close()


def update_experiment_status(
    experiment_id: str,
    status: str,
    **kwargs
) -> Optional[ExperimentRecord]:
    """Update experiment status and metadata."""
    db = SessionLocal()
    try:
        record = db.query(ExperimentRecord).filter(
            ExperimentRecord.id == experiment_id
        ).first()
        
        if record:
            record.status = status
            if status == "running" and not record.started_at:
                record.started_at = datetime.now()
            elif status in ["completed", "failed", "stopped"] and not record.completed_at:
                record.completed_at = datetime.now()
            
            for key, value in kwargs.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            
            db.commit()
            db.refresh(record)
            return record
    finally:
        db.close()
    
    return None


def get_experiment_record(experiment_id: str) -> Optional[ExperimentRecord]:
    """Get experiment record by ID."""
    db = SessionLocal()
    try:
        return db.query(ExperimentRecord).filter(
            ExperimentRecord.id == experiment_id
        ).first()
    finally:
        db.close()


def list_experiment_records(limit: int = 100, offset: int = 0) -> list[ExperimentRecord]:
    """List experiment records with pagination."""
    db = SessionLocal()
    try:
        return db.query(ExperimentRecord).order_by(
            ExperimentRecord.created_at.desc()
        ).offset(offset).limit(limit).all()
    finally:
        db.close()


def delete_experiment_record(experiment_id: str) -> bool:
    """Delete experiment record from database."""
    db = SessionLocal()
    try:
        record = db.query(ExperimentRecord).filter(
            ExperimentRecord.id == experiment_id
        ).first()
        
        if record:
            db.delete(record)
            db.commit()
            return True
        return False
    finally:
        db.close() 