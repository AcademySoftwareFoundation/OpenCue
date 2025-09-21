module Jekyll
  class LastModifiedTag < Liquid::Tag
    def initialize(tag_name, text, tokens)
      super
    end

    def render(context)
      page = context.registers[:page]
      path = page['path']
      
      # Get the last commit date for this file
      date_str = `git log -1 --format="%ad" --date=format:"%B %d, %Y" -- #{path}`.strip
      
      # Fallback to current date if git command fails
      if date_str.empty?
        date_str = Time.now.strftime("%B %d, %Y")
      end
      
      date_str
    end
  end
  
  class PageLastModified < Generator
    priority :low
    
    def generate(site)
      site.pages.each do |page|
        # Skip if already has last_modified_date
        next if page.data['last_modified_date']
        
        path = File.join(site.source, page.path)
        if File.exist?(path)
          # Get last git commit date for this file
          date = `git log -1 --format="%ad" --date=iso -- #{path}`.strip
          unless date.empty?
            page.data['last_modified_date'] = Time.parse(date)
          end
        end
      end
      
      # Also process collection documents
      site.collections.each do |name, collection|
        collection.docs.each do |doc|
          next if doc.data['last_modified_date']
          
          path = doc.path
          if File.exist?(path)
            date = `git log -1 --format="%ad" --date=iso -- #{path}`.strip
            unless date.empty?
              doc.data['last_modified_date'] = Time.parse(date)
            end
          end
        end
      end
    end
  end
end

Liquid::Template.register_tag('last_modified', Jekyll::LastModifiedTag)
