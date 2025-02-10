import json
import csv
import pandas as pd
from typing import Dict, List, Union
from datetime import datetime
import io

class ProductRecommenderAI:
    def __init__(self):
        self.required_fields = [
            'transaction_id', 'customer_id', 'transaction_date',
            'product_id', 'product_name', 'quantity', 'price_usd'
        ]


    def format_validation_report(self, df: pd.DataFrame) -> List[str]:
        """Generate a detailed validation report."""
        validation_report = []
        validation_report.append("Data Validation Report:")
        validation_report.append("-" * 50)
        
        # 1. Data Structure Validation
        validation_report.append("1. Data Structure Check:")
        validation_report.append(f"   - Number of records: {len(df)}")
        validation_report.append(f"   - Number of columns: {len(df.columns)}")
        
        # 2. Required Fields Check
        validation_report.append("\n2. Required Fields Check:")
        df_columns = set(col.lower().strip() for col in df.columns)
        for field in self.required_fields:
            status = "✓ Present" if field.lower() in df_columns else "✗ Missing"
            validation_report.append(f"   - {field}: {status}")
        
        # 3. Data Type Validation
        validation_report.append("\n3. Data Type Validation:")
        
        # Check quantity
        invalid_quantity = df[df['quantity'].isna() | (df['quantity'] <= 0)]
        quantity_status = "✓ Valid" if invalid_quantity.empty else f"✗ Found {len(invalid_quantity)} invalid records"
        validation_report.append(f"   - Quantity (positive integers): {quantity_status}")
        
        # Check price
        invalid_price = df[df['price_usd'].isna() | (df['price_usd'] <= 0)]
        price_status = "✓ Valid" if invalid_price.empty else f"✗ Found {len(invalid_price)} invalid records"
        validation_report.append(f"   - Price (positive numbers): {price_status}")
        
        # 4. Date Format Validation
        try:
            pd.to_datetime(df['transaction_date'])
            date_status = "✓ Valid"
        except:
            date_status = "✗ Invalid date format found"
        validation_report.append(f"   - Date format: {date_status}")
        
        validation_report.append("\n" + "-" * 50)
        return validation_report

    def validate_data_format(self, data: str) -> tuple[bool, str, Union[pd.DataFrame, None]]:
        """Validate the input data format and return appropriate response."""
        try:
            # Clean the input data by removing leading/trailing whitespace
            data = data.strip()
            
            # Check if data is in CSV format
            if any(field in data for field in ['transaction_id,', 'transaction_id\n']):
                # Use pandas with skipinitialspace to handle any extra spaces
                df = pd.read_csv(io.StringIO(data), skipinitialspace=True)
                # Convert column names to lowercase and strip whitespace
                df.columns = [col.strip().lower() for col in df.columns]
                return True, "Success", df
            
            # Check if data is in JSON format
            try:
                json_data = json.loads(data)
                if 'transactions' in json_data:
                    df = pd.DataFrame(json_data['transactions'])
                    # Convert column names to lowercase
                    df.columns = [col.lower() for col in df.columns]
                    return True, "Success", df
                return False, "ERROR: Invalid JSON structure. Must contain 'transactions' key.", None
            except json.JSONDecodeError:
                return False, "ERROR: Invalid data format. Please provide your data in CSV or JSON format.", None
                
        except Exception as e:
            return False, f"ERROR: Data processing failed. {str(e)}", None

    def validate_required_fields(self, df: pd.DataFrame) -> tuple[bool, str]:
        """Check if all required fields are present in the data."""
        # Convert all column names to lowercase for case-insensitive comparison
        df_columns = set(col.lower().strip() for col in df.columns)
        required_fields_lower = set(field.lower() for field in self.required_fields)
        
        missing_fields = [field for field in self.required_fields 
                         if field.lower() not in df_columns]
        
        if missing_fields:
            return False, f"ERROR: Missing required fields: {', '.join(missing_fields)}."
        return True, "Success"

    def validate_data_types(self, df: pd.DataFrame) -> tuple[bool, str]:
        """Validate data types and values in the DataFrame."""
        try:
            # Convert quantity and price to numeric, handling any non-numeric values
            df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce')
            df['price_usd'] = pd.to_numeric(df['price_usd'], errors='coerce')

            # Validate quantity is integer and positive
            invalid_quantity = df[df['quantity'].isna() | (df['quantity'] <= 0)]
            if not invalid_quantity.empty:
                return False, "ERROR: Invalid value for field(s): quantity. Must be positive integer."

            # Validate price_usd is float and positive
            invalid_price = df[df['price_usd'].isna() | (df['price_usd'] <= 0)]
            if not invalid_price.empty:
                return False, "ERROR: Invalid value for field(s): price_usd. Must be positive number."

            return True, "Success"
        except Exception as e:
            return False, f"ERROR: Data type validation failed. {str(e)}"

    def calculate_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate product metrics and importance scores."""
        # Group by product and calculate metrics
        product_metrics = df.groupby(['product_id', 'product_name']).agg({
            'quantity': 'sum',
            'price_usd': lambda x: (df.loc[x.index, 'quantity'] * x).sum()
        }).reset_index()

        product_metrics.columns = ['product_id', 'product_name', 'total_quantity', 'total_spend']
        
        # Calculate importance score
        product_metrics['importance_score'] = (
            product_metrics['total_quantity'] * 0.5 + 
            product_metrics['total_spend'] * 0.5
        )
        
        # Sort by importance score
        product_metrics = product_metrics.sort_values('importance_score', ascending=False)
        product_metrics = product_metrics.round(2)
        
        return product_metrics

    def format_transaction_details(self, df: pd.DataFrame, product_id: str) -> str:
        """Format transaction details for a specific product."""
        product_transactions = df[df['product_id'] == product_id]
        details = []
        for _, row in product_transactions.iterrows():
            details.append(
                f"Transaction {row['transaction_id']}: "
                f"{int(row['quantity'])} units × ${row['price_usd']:.2f} = "
                f"${(row['quantity'] * row['price_usd']):.2f}"
            )
        return "\n".join(details)

    def generate_response(self, data: str) -> str:
        """Generate formatted response based on the input data."""
        # Initial validation checks
        is_valid_format, format_message, df = self.validate_data_format(data)
        if not is_valid_format:
            return f"{format_message}\n\nWould you like a template for the data input?"

        # Generate validation report
        validation_report = self.format_validation_report(df)
        
        # Check if data is valid to proceed
        is_valid_fields, fields_message = self.validate_required_fields(df)
        is_valid_types, types_message = self.validate_data_types(df)
        
        if not is_valid_fields or not is_valid_types:
            return "\n".join(validation_report + [
                "\nData validation failed. Please correct the errors above.",
                "Would you like a template for the data input?"
            ])

        # If validation passes, proceed with analysis
        response = []
        response.extend(validation_report)
        response.append("\nData validation successful! Proceeding with analysis...")
        

        # Calculate metrics
        product_metrics = self.calculate_metrics(df)
        
        # Generate response with formulas and detailed calculations
        response = []
        response.extend(validation_report)
        response.append("\nData validation successful! Proceeding with analysis...")
        
        # Add formulas section
        response.append("Formulas Used:")
        response.append("1. Total Quantity Formula:")
        response.append("   Total Quantity = ∑(quantity for each transaction)")
        response.append("\n2. Total Spend Formula:")
        response.append("   Total Spend = ∑(quantity × price_usd for each transaction)")
        response.append("\n3. Importance Score Formula:")
        response.append("   Importance Score = (Total Quantity × 0.5) + (Total Spend × 0.5)")

        # Add summary
        response.append("\nSummary:")
        response.append(f"Total number of products analyzed: {len(product_metrics)}")
        
        # Add ranked list with calculations
        response.append("\nRanked List and Calculations:")
        
        # Display all products with detailed calculations
        for idx, row in product_metrics.iterrows():
            rank = idx + 1
            response.append(f"\nRank {rank}: {row['product_name']}")
            response.append("Detailed Calculations:")
            
            # Get transaction details for this product
            response.append("Individual Transactions:")
            response.append(self.format_transaction_details(df, row['product_id']))
            
            # Total Quantity calculation
            response.append("\nTotal Quantity Calculation:")
            response.append(f"Total Quantity = {int(row['total_quantity'])} units")
            
            # Total Spend calculation
            response.append("\nTotal Spend Calculation:")
            response.append(f"Total Spend = ${row['total_spend']:,.2f}")
            
            # Importance Score calculation
            response.append("\nImportance Score Calculation:")
            response.append(
                f"Importance Score = (Total Quantity × 0.5) + (Total Spend × 0.5)"
                f"\n= ({int(row['total_quantity'])} × 0.5) + ({row['total_spend']:.2f} × 0.5)"
                f"\n= {(row['total_quantity'] * 0.5):.2f} + {(row['total_spend'] * 0.5):.2f}"
                f"\n= {row['importance_score']:.2f}"
            )
            
            # Summary for this product
            response.append(f"\nProduct Summary:")
            response.append(f"- Total Quantity: {int(row['total_quantity'])} units")
            response.append(f"- Total Spend: ${row['total_spend']:,.2f}")
            response.append(f"- Importance Score: {row['importance_score']:.2f}")
            response.append("\n" + "-"*50)  # Separator between products

        if len(product_metrics) > 10:
            response.append("\nNote: All products are shown with full calculations for transparency.")

        response.append("\nWould you like detailed calculations for any specific product? Please rate this analysis from 1 to 5 stars.")
        
        return "\n".join(response)

    def process_feedback(self, rating: int) -> str:
        """Process user feedback and return appropriate response."""
        if rating >= 4:
            return "Thank you for your positive feedback!"
        return "How can we improve our product recommendations?"

# Example usage
if __name__ == "__main__":
    recommender = ProductRecommenderAI()
    
    # Example data with multiple products and transactions
    example_data = """
    transaction_id,customer_id,transaction_date,product_id,product_name,quantity,price_usd
TX100,C100,2025-03-01,P100,QuantumMouse,2,25.0
TX101,C101,2025-03-02,P101,NeonKeyboard,1,75.0
TX102,C102,2025-03-03,P102,RetroMonitor,3,150.0
TX103,C103,2025-03-04,P100,QuantumMouse,1,25.0
TX104,C104,2025-03-05,P101,NeonKeyboard,2,75.0
TX105,C105,2025-03-06,P102,RetroMonitor,2,150.0


    """
    
    # Generate and print response
    print(recommender.generate_response(example_data))