#!/bin/bash

echo "🎯 QUICK DEMO API TEST"
echo "====================="
echo ""

# Test all 4 language datasets
languages=("spanish:flores_spanish_translation" "japanese:flores_japanese_translation" "arabic:flores_arabic_translation" "chinese:flores_chinese_translation")

for lang_pair in "${languages[@]}"; do
    IFS=':' read -r lang dataset <<< "$lang_pair"
    echo "Testing $lang dataset..."
    
    response=$(curl -s "http://localhost:8000/public/get_source_sentences?dataset=$dataset&count=1")
    if echo "$response" | grep -q '"success": true'; then
        echo "✅ $lang: Source sentences API works"
    else
        echo "❌ $lang: Source sentences API failed"
    fi
done

echo ""
echo "Testing multi-language evaluation API..."
response=$(curl -s -X POST "http://localhost:8000/multi-language-gpt-evaluation" \
  -H "Content-Type: application/json" \
  -d '{"language": "spanish", "count": 1}')

if echo "$response" | grep -q '"success": true'; then
    echo "✅ Multi-language evaluation API works"
else
    echo "❌ Multi-language evaluation API failed"
fi

echo ""
echo "Testing leaderboard API..."
response=$(curl -s "http://localhost:8000/public/get_leaderboard")
if echo "$response" | grep -q '"success": true'; then
    echo "✅ Leaderboard API works"
else
    echo "❌ Leaderboard API failed"
fi

echo ""
echo "🎉 Demo APIs ready!"
echo ""
echo "📁 Demo files created:"
echo "  - demo_test_spanish.csv"
echo "  - demo_test_japanese.csv" 
echo "  - demo_test_arabic.csv"
echo "  - demo_test_chinese.csv"
echo "  - DEMO_TEST_GUIDE.md"
echo ""
echo "🚀 Start demo:"
echo "  Frontend: http://localhost:3000/evaluations"
echo "  Submit: http://localhost:3000/submit-to-leaderboard" 