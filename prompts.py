"""
Prompt templates for the OpenAI API diary entry organizer
"""

def get_diary_organization_prompt(diary_entry, ongoing_entries):
    """
    Creates a prompt for organizing a diary entry and finding related content
    
    Args:
        diary_entry: The new diary entry to organize
        ongoing_entries: Previous diary entries
        
    Returns:
        A formatted prompt for the model
    """
    prompt = f"""
    You are an intelligent diary organizer. Your task is to analyze a new diary entry and determine how it relates to previous entries, if any exist. You should categorize and organize the content to help the user maintain a structured diary.

    # PREVIOUS DIARY ENTRIES:
    {ongoing_entries if ongoing_entries else "No previous entries exist yet."}

    # NEW DIARY ENTRY:
    {diary_entry}

    Please provide a detailed analysis with the following structure:

    ## ENTRY CATEGORIZATION
    - **Main Topics**: [Identify 1-2 main topics or themes in this entry if any]
    - **Emotional Tone**: [Analyze the emotional tone of the entry]
    - **Related Previous Entries**: [Identify any connections to previous entries by topic or theme]

    ## ORGANIZED ENTRY
    [Rewrite the entry with proper formatting, paragraph breaks, and organization while preserving all original content and meaning]

    ## APPENDING STRATEGY
    [Explain where this entry should be appended in relation to previous entries. If there are related entries, suggest appending near those. If not, suggest appending at the end as a new topic.]

    ## TO-DO ITEMS
    [Extract any tasks, to-do items, or intentions mentioned in the entry, no matter how they're phrased. Look for phrases like "need to", "have to", "should", "must", "want to", "going to", etc. that indicate planned actions. If none are found, write "No to-do items detected."]

    Your goal is to help the user keep their diary well-organized while extracting actionable items.
    """
    
    return prompt 