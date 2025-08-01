# Jekyll plugin to generate search data for Lunr.js
# This creates a JSON file with all searchable content

Jekyll::Hooks.register :site, :post_write do |site|
  # Collect all documents
  search_data = {
    docs: []
  }

  # Process all pages and documents
  (site.pages + site.documents).each do |page|
    next unless page.output_ext == '.html'
    next if page.data['exclude_from_search']

    # Extract text content from HTML
    content = page.content
      .gsub(/<\/?[^>]*>/, ' ')  # Remove HTML tags
      .gsub(/\s+/, ' ')         # Normalize whitespace
      .strip
      .slice(0, 5000)          # Limit content length

    # Build search document
    doc = {
      id: page.url,
      url: page.url,
      title: page.data['title'] || 'Untitled',
      description: page.data['description'] || '',
      keywords: Array(page.data['keywords']).join(' '),
      content: content
    }

    search_data[:docs] << doc
  end

  # Write search data to JSON file
  search_json = JSON.pretty_generate(search_data)
  search_file = File.join(site.dest, 'search-data.json')
  
  File.open(search_file, 'w') do |f|
    f.write(search_json)
  end

  Jekyll.logger.info 'Search:', "Generated search data for #{search_data[:docs].length} documents"
end