#!/bin/bash
# Direct RDS Connection Test
# Tests connection to RDS without SSH tunnel (from EC2 instance)

echo "=========================================================================="
echo "              DIRECT RDS CONNECTION TEST (from EC2)"
echo "=========================================================================="
echo ""

# RDS Configuration
RDSHOST="finanza-bank.cluster-cxo2eume87bz.eu-north-1.rds.amazonaws.com"
RDSPORT=5432
RDSDB="postgres"
RDSUSER="finbank"
RDSPASS="Supposedbe5"

echo "Testing direct connection to RDS..."
echo "Host: $RDSHOST"
echo "Port: $RDSPORT"
echo "Database: $RDSDB"
echo "User: $RDSUSER"
echo ""

# Test 1: Basic connection
echo "Test 1: Testing basic connection..."
PGPASSWORD="$RDSPASS" psql -h "$RDSHOST" -p "$RDSPORT" -U "$RDSUSER" -d "$RDSDB" -c "SELECT 1 as connection_test;"

if [ $? -eq 0 ]; then
    echo "✅ Connection successful!"
else
    echo "❌ Connection failed!"
    echo ""
    echo "Trying alternate credentials..."
    
    # Try with postgres_admin user
    RDSUSER="postgres_admin"
    RDSDB="finbank"
    
    echo "Attempting with:"
    echo "  User: $RDSUSER"
    echo "  Database: $RDSDB"
    echo ""
    
    PGPASSWORD="$RDSPASS" psql -h "$RDSHOST" -p "$RDSPORT" -U "$RDSUSER" -d "$RDSDB" -c "SELECT 1 as connection_test;"
    
    if [ $? -eq 0 ]; then
        echo "✅ Connection successful with alternate credentials!"
    else
        echo "❌ Both attempts failed"
        exit 1
    fi
fi

echo ""
echo "Test 2: Listing databases..."
PGPASSWORD="$RDSPASS" psql -h "$RDSHOST" -p "$RDSPORT" -U "$RDSUSER" -c "\l"

echo ""
echo "Test 3: Checking finbank database..."
PGPASSWORD="$RDSPASS" psql -h "$RDSHOST" -p "$RDSPORT" -U "$RDSUSER" -d "finbank" -c "\dt"

echo ""
echo "=========================================================================="
echo "                     RDS CONNECTION TEST COMPLETE"
echo "=========================================================================="
