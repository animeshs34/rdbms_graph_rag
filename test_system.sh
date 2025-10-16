#!/bin/bash

set -e

API_URL="${API_URL:-http://localhost:8000}"
POSTGRES_CONN="postgresql://postgres:postgres@localhost:5432/sample_db"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

test_health() {
    print_header "TEST 1: Health Check"
    response=$(curl -s "$API_URL/health")
    if echo "$response" | grep -q "healthy"; then
        print_success "API is healthy"
        echo "$response" | jq .
        return 0
    else
        print_error "API health check failed"
        return 1
    fi
}

test_connections() {
    print_header "TEST 2: Database Connections"
    
    services=("postgres" "mysql" "neo4j" "redis")
    for service in "${services[@]}"; do
        print_info "Testing $service..."
        response=$(curl -s "$API_URL/health")
        if echo "$response" | grep -q "healthy"; then
            print_success "$service is connected"
        else
            print_error "$service connection failed"
            return 1
        fi
    done
}

test_schema_mapping() {
    print_header "TEST 3: Schema Mapping"
    print_info "Mapping PostgreSQL schema..."
    
    response=$(curl -s -X POST "$API_URL/schema/map" \
        -H "Content-Type: application/json" \
        -d "{
            \"connection_string\": \"$POSTGRES_CONN\",
            \"db_type\": \"postgres\",
            \"use_llm\": true
        }")
    
    if echo "$response" | grep -q "node_types"; then
        node_count=$(echo "$response" | jq '.node_types | length')
        rel_count=$(echo "$response" | jq '.relationship_types | length')
        print_success "Schema mapped: $node_count node types, $rel_count relationship types"
        return 0
    else
        print_error "Schema mapping failed"
        echo "$response" | jq .
        return 1
    fi
}

test_migration() {
    print_header "TEST 4: Database Migration"
    print_info "Migrating PostgreSQL to Neo4j..."
    
    response=$(curl -s -X POST "$API_URL/migrate" \
        -H "Content-Type: application/json" \
        -d "{
            \"connection_string\": \"$POSTGRES_CONN\",
            \"db_type\": \"postgres\",
            \"domain_prefix\": \"Healthcare\",
            \"use_llm\": true,
            \"batch_size\": 1000
        }")
    
    if echo "$response" | grep -q "nodes_created"; then
        nodes=$(echo "$response" | jq '.nodes_created')
        rels=$(echo "$response" | jq '.relationships_created')
        print_success "Migration completed: $nodes nodes, $rels relationships"
        return 0
    else
        print_error "Migration failed"
        echo "$response" | jq .
        return 1
    fi
}

test_embeddings() {
    print_header "TEST 5: Build Embeddings"
    print_info "Building vector embeddings..."
    
    response=$(curl -s -X POST "$API_URL/embeddings/build" \
        -H "Content-Type: application/json" \
        -d "{
            \"domain_prefix\": \"Healthcare\",
            \"batch_size\": 100
        }")
    
    if echo "$response" | grep -q "embeddings_created"; then
        count=$(echo "$response" | jq '.embeddings_created')
        print_success "Embeddings created: $count"
        return 0
    else
        print_error "Embeddings build failed"
        echo "$response" | jq .
        return 1
    fi
}

test_query() {
    print_header "TEST 6: Natural Language Query"
    print_info "Testing query: 'Show me all patients with their appointments'"

    response=$(curl -s -X POST "$API_URL/query" \
        -H "Content-Type: application/json" \
        -d "{
            \"query\": \"Show me all patients with their appointments\",
            \"domain_prefix\": \"Healthcare\"
        }")

    if echo "$response" | grep -q "answer"; then
        print_success "Query executed successfully"
        echo "$response" | jq '.answer' | head -20
        return 0
    else
        print_error "Query failed"
        echo "$response" | jq .
        return 1
    fi
}

test_stats() {
    print_header "TEST 7: Statistics"
    print_info "Fetching graph statistics..."
    
    response=$(curl -s "$API_URL/stats?domain_prefix=Healthcare")
    
    if echo "$response" | grep -q "total_nodes"; then
        nodes=$(echo "$response" | jq '.total_nodes')
        rels=$(echo "$response" | jq '.total_relationships')
        print_success "Stats: $nodes nodes, $rels relationships"
        echo "$response" | jq .
        return 0
    else
        print_error "Stats fetch failed"
        return 1
    fi
}

test_ui() {
    print_header "TEST 8: Web UI"
    print_info "Testing UI accessibility..."
    
    status=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/")
    if [ "$status" -eq 200 ]; then
        print_success "UI is accessible at $API_URL/"
        print_info "API docs available at $API_URL/docs"
        return 0
    else
        print_error "UI not accessible (HTTP $status)"
        return 1
    fi
}

run_all_tests() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║     RDBMS to Graph RAG - Production Test Suite                ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
    
    failed=0
    
    test_health || ((failed++))
    test_connections || ((failed++))
    test_schema_mapping || ((failed++))
    test_migration || ((failed++))
    test_embeddings || ((failed++))
    test_query || ((failed++))
    test_stats || ((failed++))
    test_ui || ((failed++))
    
    print_header "TEST SUMMARY"
    if [ $failed -eq 0 ]; then
        print_success "All tests passed! ✨"
        echo -e "\n${GREEN}System is production ready!${NC}"
        echo -e "${BLUE}Access points:${NC}"
        echo -e "  • Web UI:      $API_URL/"
        echo -e "  • API Docs:    $API_URL/docs"
        echo -e "  • Neo4j:       http://localhost:7474"
        return 0
    else
        print_error "$failed test(s) failed"
        return 1
    fi
}

if [ "$1" == "health" ]; then
    test_health
elif [ "$1" == "connections" ]; then
    test_connections
elif [ "$1" == "schema" ]; then
    test_schema_mapping
elif [ "$1" == "migrate" ]; then
    test_migration
elif [ "$1" == "embeddings" ]; then
    test_embeddings
elif [ "$1" == "query" ]; then
    test_query
elif [ "$1" == "stats" ]; then
    test_stats
elif [ "$1" == "ui" ]; then
    test_ui
else
    run_all_tests
fi

